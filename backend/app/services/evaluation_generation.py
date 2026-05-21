"""评估任务 SSE 流式推送（参考 distillation_generation）。"""

from __future__ import annotations

import json
import os
import queue
import threading
from collections.abc import Iterator
from datetime import datetime, timezone
from typing import Any, Callable

from app.config import evaluation_catalog as eval_cfg
from app.config import model_catalog as model_cfg
from app.services import evaluation_benchmark, evaluation_metrics, model_config_service, model_test_service

EmitFn = Callable[[dict[str, Any]], None]

_EVAL_MAX_SAMPLES = int(os.getenv("EVALUATION_MAX_SAMPLES", "0"))
_EVAL_API_MAX_TOKENS = int(os.getenv("EVALUATION_API_MAX_TOKENS", "2000"))
_EVAL_MAX_LENGTH = int(os.getenv("EVALUATION_MAX_LENGTH", "3000"))
_EVAL_LOCAL_MAX_NEW_TOKENS = int(os.getenv("EVALUATION_LOCAL_MAX_NEW_TOKENS", "1024"))
_EVAL_TEMPERATURE = float(os.getenv("EVALUATION_TEMPERATURE", "0"))

EVALUATION_STEPS = [
    {"title": "加载评估基准", "description": "读取 LP-ParamBank 基准 JSONL"},
    {"title": "加载评估模型", "description": "挂载本地权重或 API 配置"},
    {"title": "逐条 CoT 推理", "description": "流式生成思维链并解析评分"},
    {"title": "汇总指标", "description": "计算 RMSE 与精确匹配率"},
]


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%H:%M:%S")


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
    sample: dict[str, Any],
    emit: EmitFn | None,
    *,
    cancel_event: threading.Event | None = None,
) -> str:
    instruction = sample["Instruction"]
    input_text = sample["Input"]

    def on_chunk(chunk: str) -> None:
        if cancel_event and cancel_event.is_set():
            return
        _cot_delta(emit, chunk)

    if local_session is not None:
        return local_session.generate_stream(
            instruction, input_text, on_chunk=on_chunk, cancel_event=cancel_event
        )

    api = entry.get("api_config") or {}
    model_id = (api.get("model_id") or "").strip()
    if not model_id:
        raise ValueError("API 模型未配置 model_id")
    prompt = f"{instruction.rstrip()}\n\n{input_text}"
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


class EvaluationCancelled(Exception):
    """用户中止评估。"""


def run_evaluation(
    model: str,
    ground_truth: str,
    *,
    emit: EmitFn | None = None,
    cancel_event: threading.Event | None = None,
) -> dict[str, Any]:
    if ground_truth != eval_cfg.LP_PARAM_BENCHMARK_ID:
        raise ValueError("仅支持工艺参数规范库评估基准 (LP-ParamBank)")

    if cancel_event and cancel_event.is_set():
        raise EvaluationCancelled("用户已中止评估")

    entry = _resolve_model(model)
    samples = evaluation_benchmark.load_benchmark_samples(ground_truth)
    limit = len(samples) if _EVAL_MAX_SAMPLES <= 0 else min(len(samples), _EVAL_MAX_SAMPLES)

    exact_matches: list[int] = []
    mse_values: list[float] = []
    failed = 0

    _step(emit, 0, "process")
    _log(emit, f"加载评估基准：{eval_cfg.BENCHMARK_DATASETS[ground_truth]['label']}，共 {limit} 条")
    _step(emit, 0, "finish")

    if cancel_event and cancel_event.is_set():
        raise EvaluationCancelled("用户已中止评估")

    _step(emit, 1, "process")
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
    _step(emit, 1, "finish")

    _step(emit, 2, "process")
    try:
        for i, sample in enumerate(samples[:limit], start=1):
            if cancel_event and cancel_event.is_set():
                raise EvaluationCancelled("用户已中止评估")

            gold_correct = int(sample["true_correct"])
            gold_total = int(sample["true_total"])
            gold_json = {
                "correctly_predicted_relations": gold_correct,
                "total_predicted_relations": gold_total,
            }
            preview = (sample.get("passage") or "")[:48]
            _log(emit, f"[{i}/{limit}] 评估样本 | {preview}…", "INFO")
            _cot_start(emit, i, limit, preview)

            try:
                predicted_output = _predict_sample_stream(
                    entry,
                    local_session,
                    sample,
                    emit,
                    cancel_event=cancel_event,
                )
            except EvaluationCancelled:
                raise
            except RuntimeError as e:
                if "中止" in str(e):
                    raise EvaluationCancelled(str(e)) from e
                failed += 1
                _log(emit, f"  生成失败: {e}", "ERROR")
                exact_matches.append(0)
                if emit:
                    emit({"type": "cot_end", "index": i})
                continue
            except Exception as e:
                failed += 1
                _log(emit, f"  生成失败: {e}", "ERROR")
                exact_matches.append(0)
                if emit:
                    emit({"type": "cot_end", "index": i})
                continue

            if emit:
                emit({"type": "cot_end", "index": i})

            predicted_json = evaluation_metrics.extract_score_json(predicted_output)
            if predicted_json is None:
                failed += 1
                _log(emit, "  无法解析评分 JSON", "WARN")
                exact_matches.append(0)
                continue

            em = evaluation_metrics.calculate_exact_match(
                predicted_json["correctly_predicted_relations"],
                predicted_json["total_predicted_relations"],
                gold_json["correctly_predicted_relations"],
                gold_json["total_predicted_relations"],
            )
            mse = evaluation_metrics.calculate_mse(
                predicted_json["correctly_predicted_relations"],
                predicted_json["total_predicted_relations"],
                gold_json["correctly_predicted_relations"],
                gold_json["total_predicted_relations"],
            )
            exact_matches.append(em)
            mse_values.append(mse)
            _log(
                emit,
                f"  LLM: {predicted_json['correctly_predicted_relations']}/{predicted_json['total_predicted_relations']} "
                f"| Gold: {gold_correct}/{gold_total} | ExactMatch={em} MSE={mse:.4f}",
                "SUCCESS" if em else "INFO",
            )
            if emit:
                emit(
                    {
                        "type": "sample_result",
                        "index": i,
                        "exact_match": em,
                        "mse": mse,
                    }
                )

            # 状态机：随样本进度推进（0→3）
            if emit:
                step_idx = min(3, max(0, int((i / limit) * 4) - 1))
                _step(emit, step_idx, "process")
    finally:
        if local_session is not None:
            local_session.close()

    _step(emit, 2, "finish")
    _step(emit, 3, "process")

    agg = evaluation_metrics.aggregate_metrics(exact_matches, mse_values)
    rmse = agg["rmse"] if agg["rmse"] is not None else 0.0
    exact_match = agg["exact_match"]

    _log(
        emit,
        f"评估完成 | 成功 {agg['successful_samples']}/{limit} | "
        f"Exact Match={exact_match:.4f} | RMSE={rmse:.4f}",
        "SUCCESS",
    )
    _step(emit, 3, "finish")

    evaluation = {
        "rmse": rmse,
        "exactMatch": exact_match,
        "totalSamples": limit,
        "successfulSamples": agg["successful_samples"],
        "failedSamples": failed,
    }
    return {"evaluation": evaluation}


def iter_sse_lines(
    model: str,
    ground_truth: str,
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
            result = run_evaluation(
                model,
                ground_truth,
                emit=emit,
                cancel_event=cancel,
            )
            if not cancel.is_set():
                event_queue.put({"type": "done", "evaluation": result["evaluation"]})
        except EvaluationCancelled as exc:
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
    return threading.Event()
