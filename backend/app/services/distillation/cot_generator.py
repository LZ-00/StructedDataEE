"""CoT 样本生成核心逻辑。"""

from __future__ import annotations

import csv
import json
import threading
import time
from pathlib import Path
from typing import Any, Callable, Optional

from app.config import distillation_catalog as distill_cfg
from app.services import model_config_service, model_test_service
from app.services.distillation.storage import TRAINING_CSV_FIELDS, resolve_training_dataset_path

LogCallback = Callable[[str, str], None]


class GenerationCancelled(Exception):
    """用户中止或客户端断开连接时抛出。"""


def load_csv_rows(csv_path: Path) -> list[dict[str, str]]:
    if not csv_path.is_file():
        raise FileNotFoundError(f"训练数据集 CSV 不存在: {csv_path}")
    rows: list[dict[str, str]] = []
    with open(csv_path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append({k: (row.get(k) or "").strip() for k in TRAINING_CSV_FIELDS})
    return rows


def format_cot_prompt(
    instruction_template: str,
    *,
    passage: str,
    ai_predictions: str,
    true_correct: str,
    true_total: str,
) -> str:
    mapping = {
        "passage": passage,
        "ai_predictions": ai_predictions,
        "ai_prediction": ai_predictions,
        "true_correct": true_correct,
        "true_total": true_total,
    }
    try:
        return instruction_template.format(**mapping)
    except KeyError:
        return (
            f"{instruction_template.rstrip()}\n\n"
            f"Context: {passage}\n"
            f"AI Prediction: {ai_predictions}\n"
            "### Verified Evaluation Score ###\n"
            f"correctly_predicted_relations: {true_correct}\n"
            f"total_predicted_relations: {true_total}"
        )


def row_to_ui_sample(row: dict[str, str], idx: int, cot_trace: str) -> dict[str, Any]:
    correct = row.get("true_correct", "0")
    total = row.get("true_total", "0")
    return {
        "id": idx,
        "context": row.get("passage", ""),
        "ai_prediction": row.get("ai_predicted_relations", ""),
        "verified_score": f"{correct}/{total}",
        "cot_trace": cot_trace,
    }


def write_jsonl_line(record: dict[str, Any], output_path: Path, *, mode: str = "a") -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, mode, encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def peek_teacher_api(teacher_registry_id: str) -> dict[str, Any]:
    return _resolve_teacher_api(teacher_registry_id)


def _resolve_teacher_api(teacher_registry_id: str) -> dict[str, Any]:
    entry = model_config_service.get_model_internal(teacher_registry_id)
    if not entry:
        raise ValueError(f"教师模型不存在: {teacher_registry_id}")
    if entry.get("type") != "api":
        raise ValueError("当前 CoT 蒸馏仅支持 API 类教师模型，请在模型配置中添加并选择 API 模型")
    api = entry.get("api_config") or {}
    model_id = (api.get("model_id") or "").strip()
    if not model_id:
        raise ValueError("教师模型未配置 API model_id")
    return {
        "registry_id": teacher_registry_id,
        "model_id": model_id,
        "api_key": api.get("api_key", ""),
        "base_url": api.get("base_url", ""),
        "temperature": float(api.get("temperature", 0.7)),
    }


def _check_cancel(cancel_event: threading.Event | None) -> None:
    if cancel_event and cancel_event.is_set():
        raise GenerationCancelled("用户已中止生成任务")


def _invoke_teacher(
    teacher: dict[str, Any],
    prompt: str,
    *,
    max_retries: int = distill_cfg.COT_API_MAX_RETRIES,
    retry_delay: float = distill_cfg.COT_API_RETRY_DELAY_SEC,
    on_log: Optional[LogCallback] = None,
    cancel_event: threading.Event | None = None,
) -> Optional[str]:
    for attempt in range(max_retries + 1):
        _check_cancel(cancel_event)
        result = model_test_service.invoke_api_chat_completion(
            model_id=teacher["model_id"],
            api_key=teacher["api_key"],
            base_url=teacher["base_url"],
            user_content=prompt,
            temperature=teacher["temperature"],
            max_tokens=distill_cfg.COT_API_MAX_TOKENS,
        )
        if result.get("success"):
            elapsed = result.get("elapsed_seconds", "?")
            if on_log:
                on_log(f"    ✓ API 响应成功 ({elapsed}s)", "SUCCESS")
            return (result.get("content") or "").strip()
        err = result.get("message", "未知错误")
        if on_log:
            on_log(f"    ✗ API 失败 ({attempt + 1}/{max_retries + 1}): {err}", "WARN")
        if attempt < max_retries:
            if on_log:
                on_log(f"    … {retry_delay}s 后重试", "INFO")
            elapsed = 0.0
            while elapsed < retry_delay:
                _check_cancel(cancel_event)
                step = min(0.2, retry_delay - elapsed)
                time.sleep(step)
                elapsed += step
    return None


def generate_cot_preview(
    *,
    teacher_registry_id: str,
    dataset_id: str,
    instruction_template: str,
    output_path: Optional[Path] = None,
    on_log: Optional[LogCallback] = None,
    cancel_event: threading.Event | None = None,
) -> dict[str, Any]:
    csv_path = resolve_training_dataset_path(dataset_id)
    rows = load_csv_rows(csv_path)
    if not rows:
        raise ValueError(f"数据集为空: {csv_path}")

    total_rows = len(rows)
    teacher = _resolve_teacher_api(teacher_registry_id)
    run_timestamp = distill_cfg.generation_timestamp_slug()
    safe_teacher = teacher_registry_id.replace("/", "_").replace(".", "_")
    safe_dataset = dataset_id.replace("/", "_").replace(".", "_").replace(":", "_")
    out_path = output_path or (distill_cfg.OUTPUT_DIR / f"cot_{safe_dataset}_{safe_teacher}_{run_timestamp}.jsonl")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8"):
        pass

    if on_log:
        on_log(f"  → 输出 JSONL: {out_path.name}（本次任务 {run_timestamp}）", "INFO")

    samples: list[dict[str, Any]] = []
    failed_indices: list[int] = []
    errors: list[str] = []

    for idx, row in enumerate(rows, start=1):
        _check_cancel(cancel_event)
        if on_log:
            preview = (row["passage"][:48] + "…") if len(row["passage"]) > 48 else row["passage"]
            on_log(f"  → [{idx}/{total_rows}] 调用教师模型 | {preview}", "INFO")
        prompt = format_cot_prompt(
            instruction_template,
            passage=row["passage"],
            ai_predictions=row["ai_predicted_relations"],
            true_correct=row["true_correct"],
            true_total=row["true_total"],
        )
        cot_response = _invoke_teacher(teacher, prompt, on_log=on_log, cancel_event=cancel_event)
        if not cot_response:
            failed_indices.append(idx)
            errors.append(f"第 {idx} 条 API 生成失败")
            continue

        record = {
            "index": idx,
            "passage": row["passage"],
            "ai_predictions": row["ai_predicted_relations"],
            "true_correct": row["true_correct"],
            "true_total": row["true_total"],
            "prompt": prompt,
            "cot_response": cot_response,
            "teacher_model": teacher_registry_id,
            "training_dataset": dataset_id,
            "run_timestamp": run_timestamp,
        }
        write_jsonl_line(record, out_path)
        samples.append(row_to_ui_sample(row, idx, cot_response))
        if on_log:
            on_log(f"    → 已写入 JSONL (#{idx})", "INFO")

    return {
        "samples": samples,
        "total_rows": total_rows,
        "processed_rows": total_rows,
        "generated_count": len(samples),
        "failed_indices": failed_indices,
        "output_path": str(out_path),
        "run_timestamp": run_timestamp,
        "errors": errors,
    }
