"""上传数据思维链评估运行器（SSE）。"""

from __future__ import annotations

import json
import os
import queue
import re
import threading
from collections.abc import Iterator
from typing import Any, Callable

from app.config import model_catalog as model_cfg
from app.services import model_config_service, model_test_service
from app.services.evaluate.sample_builder import EvaluationSample
from app.timezone_utils import time_now_asia_shanghai

EmitFn = Callable[[dict[str, Any]], None]

_EVAL_API_MAX_TOKENS = int(os.getenv("EVALUATION_API_MAX_TOKENS", "2000"))
_EVAL_MAX_LENGTH = int(os.getenv("EVALUATION_MAX_LENGTH", "3000"))
_EVAL_LOCAL_MAX_NEW_TOKENS = int(os.getenv("EVALUATION_LOCAL_MAX_NEW_TOKENS", "1024"))
_EVAL_TEMPERATURE = float(os.getenv("EVALUATION_TEMPERATURE", "0"))

EVALUATION_STEPS = [
    {"title": "Step 1 解析字段", "description": "解析 AI Prediction 中所有非空字段-值对"},
    {"title": "Step 2 证据核验", "description": "仅基于 Context 核验字段值与单位"},
    {"title": "Step 3 关系诊断", "description": "按字段、值、单位、关联关系判定正误"},
    {"title": "Step 4 评分统合", "description": "统计正确预测数与非空预测总数"},
]


class EvaluationCancelled(Exception):
    """用户中止评估。"""


def _ts() -> str:
    return time_now_asia_shanghai()


def _step(emit: EmitFn | None, index: int, status: str) -> None:
    if emit:
        emit({"type": "step", "index": index, "status": status})


def _log(emit: EmitFn | None, message: str, level: str = "INFO") -> None:
    if emit:
        emit({"type": "log", "time": _ts(), "level": level, "message": message})


def _cot_delta(emit: EmitFn | None, text: str) -> None:
    if emit and text:
        emit({"type": "cot_delta", "text": text})


def _cot_start(emit: EmitFn | None, index: int, total: int, preview: str) -> None:
    if emit:
        emit({"type": "cot_start", "index": index, "total": total, "preview": preview})


def _resolve_model(registry_id: str) -> dict[str, Any]:
    entry = model_config_service.get_model_internal(registry_id)
    if not entry:
        raise ValueError(f"评估模型不存在: {registry_id}")
    return entry


def _preview_text(text: str, *, max_len: int = 64) -> str:
    content = (text or "").strip()
    if len(content) <= max_len:
        return content
    return f"{content[:max_len]}..."


def _open_local_session(entry: dict[str, Any]) -> model_test_service.LocalInferenceSession:
    lc = entry.get("local_config") or {}
    ms_id = (lc.get("model_id") or "").strip()
    if not ms_id:
        raise ValueError("本地模型未配置 model_id")
    base_dir = (lc.get("base_dir") or model_cfg.DEFAULT_LOCAL_BASE_DIR).strip()
    custom_path = (lc.get("local_path") or "").strip()
    model_test_service.validate_local_model_downloaded(ms_id, base_dir, custom_path)
    return model_test_service.open_local_inference_session(
        ms_id,
        base_dir,
        custom_path,
        max_new_tokens=_EVAL_LOCAL_MAX_NEW_TOKENS,
        max_length=_EVAL_MAX_LENGTH,
        temperature=_EVAL_TEMPERATURE,
    )


def _predict_sample_stream(
    entry: dict[str, Any],
    local_session: model_test_service.LocalInferenceSession | None,
    sample: EvaluationSample,
    emit: EmitFn | None,
    *,
    cancel_event: threading.Event | None = None,
    on_text: Callable[[str], None] | None = None,
) -> str:
    if cancel_event and cancel_event.is_set():
        raise EvaluationCancelled("用户已中止评估")

    def on_chunk(chunk: str) -> None:
        if cancel_event and cancel_event.is_set():
            return
        if on_text:
            on_text(chunk)
        _cot_delta(emit, chunk)

    if local_session is not None:
        return local_session.generate_stream(
            sample.instruction,
            sample.input_text,
            on_chunk=on_chunk,
            cancel_event=cancel_event,
        )

    api = entry.get("api_config") or {}
    model_id = (api.get("model_id") or "").strip()
    if not model_id:
        raise ValueError("API 模型未配置 model_id")
    prompt = f"{sample.instruction.rstrip()}\n\n{sample.input_text}"
    return model_test_service.invoke_api_chat_completion_stream(
        model_id=model_id,
        api_key=api.get("api_key", ""),
        base_url=api.get("base_url", ""),
        user_content=prompt,
        temperature=_EVAL_TEMPERATURE,
        max_tokens=_EVAL_API_MAX_TOKENS,
        on_chunk=on_chunk,
        cancel_event=cancel_event,
    )


def _create_step_tracker(emit: EmitFn | None) -> tuple[Callable[[str], None], Callable[[], None]]:
    markers = ("step 1", "step 2", "step 3", "step 4")
    seen = [False, False, False, False]
    finished = [False, False, False, False]
    active: int | None = None
    text_buffer = ""

    def consume(text: str) -> None:
        nonlocal active, text_buffer
        if not text:
            return
        text_buffer += text.lower()
        for idx, marker in enumerate(markers):
            if seen[idx] or marker not in text_buffer:
                continue
            seen[idx] = True
            if active is not None and active != idx and not finished[active]:
                _step(emit, active, "finish")
                finished[active] = True
            _step(emit, idx, "process")
            active = idx

    def finalize() -> None:
        nonlocal active
        if not any(seen):
            for idx in range(4):
                _step(emit, idx, "process")
                _step(emit, idx, "finish")
            return
        if active is not None and not finished[active]:
            _step(emit, active, "finish")
            finished[active] = True
        for idx in range(4):
            if seen[idx] and not finished[idx]:
                _step(emit, idx, "finish")
                finished[idx] = True

    return consume, finalize


def run_uploaded_evaluation(
    model: str,
    samples: list[EvaluationSample],
    *,
    emit: EmitFn | None = None,
    cancel_event: threading.Event | None = None,
) -> dict[str, Any]:
    if cancel_event and cancel_event.is_set():
        raise EvaluationCancelled("用户已中止评估")
    if not samples:
        raise ValueError("没有可评估的记录")

    total = len(samples)
    results: list[dict[str, Any]] = []
    failed = 0

    _log(emit, f"上传记录解析完成，共 {total} 条有效记录")

    entry = _resolve_model(model)
    local_session: model_test_service.LocalInferenceSession | None = None
    if entry.get("type") == "local":
        local_session = _open_local_session(entry)
        base_path, adapter = model_test_service.resolve_local_weights(
            (entry.get("local_config") or {}).get("model_id", ""),
            (entry.get("local_config") or {}).get("base_dir", model_cfg.DEFAULT_LOCAL_BASE_DIR),
            (entry.get("local_config") or {}).get("local_path", ""),
        )
        _log(emit, f"本地模型已加载：{base_path}" + (f" + LoRA {adapter}" if adapter else ""))
    else:
        api = entry.get("api_config") or {}
        _log(emit, f"API 模型：{api.get('model_id', '')}")
    try:
        for i, sample in enumerate(samples, start=1):
            if cancel_event and cancel_event.is_set():
                raise EvaluationCancelled("用户已中止评估")
            preview = _preview_text(sample.passage, max_len=64)
            _log(emit, f"[{i}/{total}] 评估记录 {sample.record_id} | {preview}")
            _cot_start(emit, i, total, preview)
            on_text, finalize_steps = _create_step_tracker(emit)
            try:
                predicted_output = _predict_sample_stream(
                    entry,
                    local_session,
                    sample,
                    emit,
                    cancel_event=cancel_event,
                    on_text=on_text,
                )
            except EvaluationCancelled:
                raise
            except RuntimeError as exc:
                if "中止" in str(exc):
                    raise EvaluationCancelled(str(exc)) from exc
                failed += 1
                _log(emit, f"  推理失败: {exc}", "ERROR")
                results.append(
                    {
                        "index": i,
                        "recordId": sample.record_id,
                        "chunkId": sample.chunk_id,
                        "preview": preview,
                        "status": "failed",
                        "analysis": "",
                        "score": None,
                    }
                )
                if emit:
                    emit({"type": "cot_end", "index": i})
                continue
            except Exception as exc:
                failed += 1
                _log(emit, f"  推理失败: {exc}", "ERROR")
                results.append(
                    {
                        "index": i,
                        "recordId": sample.record_id,
                        "chunkId": sample.chunk_id,
                        "preview": preview,
                        "status": "failed",
                        "analysis": "",
                        "score": None,
                    }
                )
                if emit:
                    emit({"type": "cot_end", "index": i})
                continue

            finalize_steps()
            if emit:
                emit({"type": "cot_end", "index": i})
            score = _extract_score_json(predicted_output)
            item = {
                "index": i,
                "recordId": sample.record_id,
                "chunkId": sample.chunk_id,
                "preview": preview,
                "status": "success",
                "analysis": predicted_output,
                "score": score,
            }
            results.append(item)
            _log(emit, f"  记录 {sample.record_id} 评估完成", "SUCCESS")
            if emit:
                emit({"type": "sample_result", "record": item})
    finally:
        if local_session is not None:
            local_session.close()
    summary = {
        "totalRecords": total,
        "successfulRecords": total - failed,
        "failedRecords": failed,
    }
    _log(
        emit,
        f"评估完成 | 成功 {summary['successfulRecords']}/{summary['totalRecords']} | 失败 {summary['failedRecords']}",
        "SUCCESS",
    )
    return {"summary": summary, "records": results}


def iter_uploaded_sse_lines(
    model: str,
    samples: list[EvaluationSample],
    *,
    cancel_event: threading.Event | None = None,
) -> Iterator[str]:
    cancel = cancel_event or threading.Event()
    yield f"data: {json.dumps({'type': 'step_init', 'steps': EVALUATION_STEPS}, ensure_ascii=False)}\n\n"

    event_queue: queue.Queue[dict[str, Any] | None] = queue.Queue()

    def emit(event: dict[str, Any]) -> None:
        event_queue.put(event)

    def worker() -> None:
        try:
            result = run_uploaded_evaluation(
                model,
                samples,
                emit=emit,
                cancel_event=cancel,
            )
            if not cancel.is_set():
                event_queue.put({"type": "done", "evaluation": result})
        except EvaluationCancelled as exc:
            event_queue.put({"type": "cancelled", "message": str(exc)})
        except Exception as exc:
            if not cancel.is_set():
                event_queue.put({"type": "error", "message": str(exc)})
        finally:
            event_queue.put(None)

    threading.Thread(target=worker, daemon=True).start()

    while True:
        try:
            item = event_queue.get(timeout=0.25)
        except queue.Empty:
            if cancel.is_set():
                break
            continue
        if item is None:
            break
        yield f"data: {json.dumps(item, ensure_ascii=False)}\n\n"


def request_cancel_event() -> threading.Event:
    return threading.Event()


def _extract_score_json(output: str) -> dict[str, int] | None:
    matches = re.findall(r"\{[^{}]*\}", output or "")
    for candidate in reversed(matches):
        try:
            data = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if not isinstance(data, dict):
            continue
        correct = data.get("correctly_predicted_relations")
        total = data.get("total_predicted_relations")
        if isinstance(correct, int) and isinstance(total, int):
            return {
                "correctly_predicted_relations": correct,
                "total_predicted_relations": total,
            }
    return None
