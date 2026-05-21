"""CoT 数据集生成流程与 SSE 事件推送。"""

from __future__ import annotations

import json
import queue
import threading
from collections.abc import Iterator
from datetime import datetime, timezone
from typing import Any, Callable

from app.config import distillation_catalog as distill_cfg
from app.services import cot_generation_service
from app.services.cot_generation_service import GenerationCancelled, load_csv_rows
from app.services.distillation_service import _default_instruction

EmitFn = Callable[[dict[str, Any]], None]

# 同一进程内仅允许一个 CoT 生成任务，避免并发写同一逻辑输出或重复调用 API
_generation_lock = threading.Lock()

GENERATION_STEPS = [
    {"title": "加载训练数据", "description": "读取 CSV 并校验字段"},
    {"title": "初始化教师模型", "description": "解析 API 配置与指导指令"},
    {"title": "生成 CoT 轨迹", "description": "调用教师模型逐条合成推理链"},
    {"title": "写入与汇总", "description": "保存 JSONL 并合并预览样本"},
]


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%H:%M:%S")


def _log(emit: EmitFn | None, message: str, level: str = "INFO") -> None:
    if emit:
        emit({"type": "log", "level": level, "time": _ts(), "message": message})


def _step(emit: EmitFn | None, index: int, status: str) -> None:
    if emit:
        emit({"type": "step", "index": index, "status": status})


def _fail(message: str, errors: list[str] | None = None) -> ValueError:
    detail = message
    if errors:
        detail = f"{message}；{'；'.join(errors[:5])}"
    return ValueError(detail)


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
    """执行完整生成流程；emit 用于实时推送日志与步骤。仅通过教师 API 生成，失败即报错。"""
    if cancel_event and cancel_event.is_set():
        raise GenerationCancelled("用户已中止生成任务")

    if not teacher_model or not training_dataset:
        raise ValueError("教师模型与训练数据集不能为空")
    if training_dataset not in distill_cfg.TRAINING_DATASETS:
        raise ValueError(f"不支持的数据集: {training_dataset}")

    if not _generation_lock.acquire(blocking=False):
        raise ValueError("已有 CoT 生成任务在运行，请等待完成或中止后再试")

    try:
        return _run_generation_locked(
            teacher_model,
            training_dataset,
            instruction,
            emit=emit,
            cancel_event=cancel_event,
        )
    finally:
        _generation_lock.release()


def _run_generation_locked(
    teacher_model: str,
    training_dataset: str,
    instruction: str,
    *,
    emit: EmitFn | None = None,
    cancel_event: threading.Event | None = None,
) -> dict[str, Any]:
    _step(emit, 0, "process")
    _log(emit, "[Step 1/4] 加载训练数据集")
    instruction_template = (instruction or "").strip() or _default_instruction()
    csv_path = distill_cfg.dataset_csv_path(training_dataset)
    rows = load_csv_rows(csv_path)
    if not rows:
        raise ValueError(f"数据集为空: {csv_path}")
    total_rows = len(rows)
    ui_limit = _preview_limit(total_rows)
    _log(emit, f"  → 数据集: {training_dataset} | CSV: {csv_path.name}")
    _log(emit, f"  → 数据集共 {total_rows} 条 | 将全部用于 API 生成")
    if ui_limit < total_rows:
        _log(emit, f"  → UI 预览展示前 {ui_limit} 条（不影响 JSONL 写入条数）")
    _step(emit, 0, "finish")

    if cancel_event and cancel_event.is_set():
        raise GenerationCancelled("用户已中止生成任务")

    _step(emit, 1, "process")
    _log(emit, "[Step 2/4] 初始化教师模型")
    try:
        teacher_info = cot_generation_service.peek_teacher_api(teacher_model)
    except ValueError as exc:
        _log(emit, f"  → {exc}", "ERROR")
        _step(emit, 1, "error")
        raise _fail(str(exc)) from exc
    _log(emit, f"  → 注册 ID: {teacher_model}")
    _log(emit, f"  → API model: {teacher_info['model_id']}")
    base = teacher_info.get("base_url") or "(OpenAI 默认端点)"
    _log(emit, f"  → base_url: {base}")
    _log(emit, f"  → 指导指令: {len(instruction_template)} 字符")
    _step(emit, 1, "finish")

    if cancel_event and cancel_event.is_set():
        raise GenerationCancelled("用户已中止生成任务")

    _step(emit, 2, "process")
    _log(emit, "[Step 3/4] 生成 CoT 轨迹 (generate_cot_dataset)")
    gen_errors: list[str] = []
    teacher_generated = 0
    output_path = ""
    preview_samples: list[dict[str, Any]] = []
    gen_result: dict[str, Any] = {}

    try:

        def cot_log(msg: str, level: str = "INFO") -> None:
            _log(emit, msg, level)

        gen_result = cot_generation_service.generate_cot_preview(
            teacher_registry_id=teacher_model,
            dataset_id=training_dataset,
            instruction_template=instruction_template,
            on_log=cot_log,
            cancel_event=cancel_event,
        )
        teacher_samples = gen_result.get("samples") or []
        teacher_generated = gen_result.get("generated_count", 0)
        output_path = gen_result.get("output_path", "")
        gen_errors = gen_result.get("errors") or []

        if not teacher_samples:
            for err in gen_errors:
                _log(emit, f"  → {err}", "WARN")
            _step(emit, 2, "error")
            raise _fail("教师模型未生成任何 CoT 样本", gen_errors)

        preview_samples = teacher_samples[:ui_limit]
        _log(emit, f"  → 教师模型成功: {teacher_generated} 条")
        for err in gen_errors:
            _log(emit, f"  → {err}", "WARN")
    except GenerationCancelled:
        _step(emit, 2, "error")
        raise
    except ValueError:
        _step(emit, 2, "error")
        raise
    except FileNotFoundError as exc:
        _step(emit, 2, "error")
        _log(emit, f"  → 异常: {exc}", "ERROR")
        raise _fail(str(exc)) from exc

    _step(emit, 2, "finish")

    _step(emit, 3, "process")
    _log(emit, "[Step 4/4] 写入与汇总")
    if output_path:
        _log(emit, f"  → JSONL: {output_path}")
    _log(emit, f"  → 预览 {len(preview_samples)} 条")
    _step(emit, 3, "finish")

    message = f"教师模型已生成 {teacher_generated} 条 CoT（数据集共 {total_rows} 条）"
    if gen_errors:
        message += f"，{len(gen_errors)} 条失败"

    run_timestamp = gen_result.get("run_timestamp", "")

    return {
        "success": True,
        "sample_count": total_rows,
        "preview_count": len(preview_samples),
        "teacher_model": teacher_model,
        "training_dataset": training_dataset,
        "teacher_generated_count": teacher_generated,
        "samples": preview_samples,
        "output_path": output_path,
        "run_timestamp": run_timestamp,
        "dataset_csv": str(csv_path),
        "errors": gen_errors,
        "message": message,
    }


def iter_sse_lines(
    teacher_model: str,
    training_dataset: str,
    instruction: str,
    *,
    cancel_event: threading.Event | None = None,
) -> Iterator[str]:
    """产出 SSE `data:` 行（后台线程执行生成，主线程实时推送）。"""
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
        except Exception as exc:
            if not cancel.is_set():
                event_queue.put({"type": "error", "message": str(exc)})
        finally:
            event_queue.put(None)

    threading.Thread(target=worker, daemon=True).start()

    poll_sec = 0.25
    while True:
        try:
            item = event_queue.get(timeout=poll_sec)
        except queue.Empty:
            if cancel.is_set():
                break
            continue
        if item is None:
            break
        yield f"data: {json.dumps(item, ensure_ascii=False)}\n\n"


def request_cancel_event() -> threading.Event:
    """为单次 SSE 请求创建中止信号。"""
    return threading.Event()
