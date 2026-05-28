"""CoT 生成流程与 SSE 事件推送。"""

from __future__ import annotations

import json
import queue
import threading
from collections.abc import Iterator
from typing import Any, Callable

from app.config import distillation_catalog as distill_cfg
from app.data.prompt import get_distillation_instruction_template
from app.services.distillation import cot_generator
from app.services.distillation.cot_generator import GenerationCancelled
from app.services.distillation.storage import resolve_training_dataset_path
from app.timezone_utils import time_now_asia_shanghai

EmitFn = Callable[[dict[str, Any]], None]

_active_state_lock = threading.Lock()
_active_cancel_event: threading.Event | None = None

GENERATION_STEPS = [
    {"title": "加载训练数据", "description": "读取 CSV 并校验字段"},
    {"title": "初始化教师模型", "description": "解析 API 配置与指导指令"},
    {"title": "生成 CoT 轨迹", "description": "调用教师模型逐条合成推理链"},
    {"title": "写入与汇总", "description": "保存 JSONL 并合并预览样本"},
]


def _ts() -> str:
    return time_now_asia_shanghai()


def _log(emit: EmitFn | None, message: str, level: str = "INFO") -> None:
    if emit:
        emit({"type": "log", "level": level, "time": _ts(), "message": message})


def _step(emit: EmitFn | None, index: int, status: str) -> None:
    if emit:
        emit({"type": "step", "index": index, "status": status})


def _preview_limit(total_rows: int) -> int:
    cap = distill_cfg.COT_UI_PREVIEW_MAX_ROWS
    if cap <= 0:
        return total_rows
    return min(cap, total_rows)


def run_generation(
    teacher_model: str,
    training_dataset: str,
    instruction: str,
    *,
    emit: EmitFn | None = None,
    cancel_event: threading.Event | None = None,
) -> dict[str, Any]:
    if cancel_event and cancel_event.is_set():
        raise GenerationCancelled("用户已中止生成任务")

    if not teacher_model or not training_dataset:
        raise ValueError("教师模型与训练数据集不能为空")

    _step(emit, 0, "process")
    _log(emit, "[Step 1/4] 加载训练数据集")
    csv_path = resolve_training_dataset_path(training_dataset)
    rows = cot_generator.load_csv_rows(csv_path)
    if not rows:
        raise ValueError(f"数据集为空: {csv_path}")
    total_rows = len(rows)
    ui_limit = _preview_limit(total_rows)
    _log(emit, f"  → 数据集: {training_dataset} | CSV: {csv_path.name}")
    _log(emit, f"  → 数据集共 {total_rows} 条 | 将全部用于 API 生成")
    if ui_limit < total_rows:
        _log(emit, f"  → UI 预览展示前 {ui_limit} 条（不影响 JSONL 写入条数）")
    _step(emit, 0, "finish")

    _step(emit, 1, "process")
    _log(emit, "[Step 2/4] 初始化教师模型")
    teacher_info = cot_generator.peek_teacher_api(teacher_model)
    _log(emit, f"  → 注册 ID: {teacher_model}")
    _log(emit, f"  → API model: {teacher_info['model_id']}")
    base = teacher_info.get("base_url") or "(OpenAI 默认端点)"
    _log(emit, f"  → base_url: {base}")
    instruction_template = (instruction or "").strip() or get_distillation_instruction_template()
    _log(emit, f"  → 指导指令: {len(instruction_template)} 字符")
    _step(emit, 1, "finish")

    _step(emit, 2, "process")
    _log(emit, "[Step 3/4] 生成 CoT 轨迹")
    gen_result = cot_generator.generate_cot_preview(
        teacher_registry_id=teacher_model,
        dataset_id=training_dataset,
        instruction_template=instruction_template,
        on_log=lambda msg, level="INFO": _log(emit, msg, level),
        cancel_event=cancel_event,
    )
    teacher_samples = gen_result.get("samples") or []
    if not teacher_samples:
        _step(emit, 2, "error")
        raise ValueError("教师模型未生成任何 CoT 样本")
    _step(emit, 2, "finish")

    _step(emit, 3, "process")
    preview_samples = teacher_samples[:ui_limit]
    _log(emit, "[Step 4/4] 写入与汇总")
    _log(emit, f"  → JSONL: {gen_result.get('output_path')}")
    _log(emit, f"  → 预览 {len(preview_samples)} 条")
    _step(emit, 3, "finish")

    return {
        "success": True,
        "sample_count": total_rows,
        "preview_count": len(preview_samples),
        "teacher_model": teacher_model,
        "training_dataset": training_dataset,
        "teacher_generated_count": gen_result.get("generated_count", len(teacher_samples)),
        "samples": preview_samples,
        "output_path": gen_result.get("output_path", ""),
        "run_timestamp": gen_result.get("run_timestamp", ""),
        "dataset_csv": str(csv_path),
        "errors": gen_result.get("errors", []),
        "message": f"教师模型已生成 {gen_result.get('generated_count', len(teacher_samples))} 条 CoT",
    }


def iter_sse_lines(
    teacher_model: str,
    training_dataset: str,
    instruction: str,
    *,
    cancel_event: threading.Event | None = None,
) -> Iterator[str]:
    cancel = cancel_event or threading.Event()
    yield f"data: {json.dumps({'type': 'step_init', 'steps': GENERATION_STEPS}, ensure_ascii=False)}\n\n"
    event_queue: queue.Queue[dict[str, Any] | None] = queue.Queue()

    def emit(event: dict[str, Any]) -> None:
        event_queue.put(event)

    def worker() -> None:
        try:
            result = run_generation(
                teacher_model,
                training_dataset,
                instruction,
                emit=emit,
                cancel_event=cancel,
            )
            if not cancel.is_set():
                event_queue.put({"type": "done", "result": result})
        except GenerationCancelled as exc:
            event_queue.put({"type": "cancelled", "message": str(exc)})
        except Exception as exc:  # noqa: BLE001
            if not cancel.is_set():
                event_queue.put({"type": "error", "message": str(exc)})
        finally:
            _clear_active_cancel_event(cancel)
            event_queue.put(None)

    threading.Thread(target=worker, daemon=True).start()

    while True:
        item = event_queue.get()
        if item is None:
            break
        yield f"data: {json.dumps(item, ensure_ascii=False)}\n\n"


def request_cancel_event() -> threading.Event:
    global _active_cancel_event
    new_event = threading.Event()
    with _active_state_lock:
        prev = _active_cancel_event
        _active_cancel_event = new_event
    if prev and not prev.is_set():
        prev.set()
    return new_event


def _clear_active_cancel_event(event: threading.Event) -> None:
    global _active_cancel_event
    with _active_state_lock:
        if _active_cancel_event is event:
            _active_cancel_event = None
