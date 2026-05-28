"""蒸馏业务门面。"""

from __future__ import annotations

import json
import re
from typing import Any

from app.config import distillation_catalog as distill_cfg
from app.data.prompt import get_distillation_instruction_template
from app.finetune import catalog as ft_catalog
from app.services import model_config_service
from app.services.distillation import generation
from app.services.distillation.storage import (
    build_training_dataset_options,
    dataset_file_slug,
    list_recent_finetune_datasets,
    prune_finetune_datasets,
    resolve_training_dataset_path,
    save_uploaded_training_csv,
    training_template_csv,
)

_SCORE_JSON_RE = re.compile(
    r'\{\s*"correctly_predicted_relations"\s*:\s*\d+\s*,\s*"total_predicted_relations"\s*:\s*\d+\s*\}\s*$'
)


def default_instruction() -> str:
    return get_distillation_instruction_template()


def _finetune_instruction_text() -> str:
    if ft_catalog.INSTRUCTION_FILE.is_file():
        return ft_catalog.INSTRUCTION_FILE.read_text(encoding="utf-8").strip()
    return default_instruction().strip()


def _parse_verified_score(score: str) -> tuple[int, int]:
    parts = (score or "0/0").strip().split("/")
    if len(parts) != 2:
        return 0, 0
    try:
        return int(parts[0].strip()), int(parts[1].strip())
    except ValueError:
        return 0, 0


def _build_finetune_input(sample: dict[str, Any]) -> str:
    correct, total = _parse_verified_score(str(sample.get("verified_score", "0/0")))
    return (
        "[Task Description]\n"
        "Evaluate welding relation extraction.\n\n"
        f"[Context]\n{sample.get('context', '')}\n\n"
        f"[AI Prediction]\n{sample.get('ai_prediction', '')}\n\n"
        "### Verified Evaluation Score ###\n"
        f"correctly_predicted_relations: {correct}\n"
        f"total_predicted_relations: {total}"
    )


def _build_finetune_output(sample: dict[str, Any]) -> str:
    cot_trace = (sample.get("cot_trace") or "").strip()
    if not cot_trace:
        raise ValueError(f"样本 #{sample.get('id')} 的思维链轨迹不能为空")
    correct, total = _parse_verified_score(str(sample.get("verified_score", "0/0")))
    score_json = (
        f'{{"correctly_predicted_relations": {correct}, '
        f'"total_predicted_relations": {total}}}'
    )
    if _SCORE_JSON_RE.search(cot_trace):
        return cot_trace
    return f"{cot_trace}\n{score_json}"


def _sample_to_finetune_record(sample: dict[str, Any]) -> dict[str, str]:
    return {
        "Instruction": _finetune_instruction_text(),
        "Input": _build_finetune_input(sample),
        "Output": _build_finetune_output(sample),
    }


def get_distillation_options() -> dict[str, Any]:
    datasets, default_dataset = build_training_dataset_options()
    return {
        "teacher_models": model_config_service.get_select_options(
            usage="distillation_teacher",
            types=["api"],
        ),
        "training_datasets": datasets,
        "default_training_dataset": default_dataset,
        "default_instruction": default_instruction(),
    }


def generate_distillation_dataset(
    teacher_model: str,
    training_dataset: str,
    instruction: str,
) -> dict[str, Any]:
    return generation.run_generation(teacher_model, training_dataset, instruction)


def upload_training_dataset(filename: str, raw: bytes) -> dict[str, Any]:
    meta = save_uploaded_training_csv(filename, raw)
    return {
        "success": True,
        "dataset": {
            "value": meta.dataset_id,
            "label": meta.label,
            "path": str(meta.path),
            "modified_at": meta.modified_at,
        },
        "message": "训练数据集上传成功",
    }


def training_dataset_template_content() -> str:
    return training_template_csv()


def list_recent_finetune_records() -> dict[str, Any]:
    datasets = list_recent_finetune_datasets(limit=3)
    return {
        "success": True,
        "datasets": datasets,
    }


def save_distillation_finetune_dataset(
    teacher_model: str,
    training_dataset: str,
    samples: list[dict[str, Any]],
) -> dict[str, Any]:
    if not samples:
        raise ValueError("保存样本列表不能为空")
    _ = resolve_training_dataset_path(training_dataset)

    run_timestamp = distill_cfg.generation_timestamp_slug()
    safe_teacher = teacher_model.replace("/", "_").replace(".", "_")
    safe_dataset = dataset_file_slug(training_dataset)
    out_path = distill_cfg.OUTPUT_DIR / f"finetune_{safe_dataset}_{safe_teacher}_{run_timestamp}.jsonl"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    records: list[dict[str, str]] = []
    saved_ids: list[int] = []
    for sample in sorted(samples, key=lambda s: int(s.get("id") or 0)):
        sid = sample.get("id")
        records.append(_sample_to_finetune_record(sample))
        if sid is not None:
            saved_ids.append(int(sid))

    with open(out_path, "w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    removed = prune_finetune_datasets(limit=3)
    return {
        "success": True,
        "saved_count": len(records),
        "saved_ids": saved_ids,
        "teacher_model": teacher_model,
        "training_dataset": training_dataset,
        "save_path": str(out_path),
        "run_timestamp": run_timestamp,
        "removed_records": removed,
        "message": f"已保存 {len(records)} 条校对数据，当前保留最新 3 条微调数据",
    }


def request_cancel_event():
    return generation.request_cancel_event()


def iter_sse_lines(teacher_model: str, training_dataset: str, instruction: str, *, cancel_event=None):
    return generation.iter_sse_lines(
        teacher_model,
        training_dataset,
        instruction,
        cancel_event=cancel_event,
    )
