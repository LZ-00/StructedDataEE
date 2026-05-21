"""思维链蒸馏数据构建业务逻辑。"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from app.config import distillation_catalog as distill_cfg
from app.finetune import catalog as ft_catalog
from app.services import model_config_service

_INSTRUCTION_PATH = Path(__file__).with_name("distillation_default_instruction.txt")
_LP_PARAM_DATASET = distill_cfg.LP_PARAM_DATASET_ID
_SCORE_JSON_RE = re.compile(
    r'\{\s*"correctly_predicted_relations"\s*:\s*\d+\s*,\s*"total_predicted_relations"\s*:\s*\d+\s*\}\s*$'
)


def _default_instruction() -> str:
    if _INSTRUCTION_PATH.is_file():
        return _INSTRUCTION_PATH.read_text(encoding="utf-8")
    return ""


def _finetune_instruction_text() -> str:
    if ft_catalog.INSTRUCTION_FILE.is_file():
        return ft_catalog.INSTRUCTION_FILE.read_text(encoding="utf-8").strip()
    return _default_instruction().strip() or (
        "You are an expert laser welding process engineer. "
        "Synthesize a CoT trace that justifies the verified score."
    )


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
        f"[Gold Standard]\n{sample.get('gold_standard', '')}\n\n"
        f"[AI Prediction]\n{sample.get('ai_prediction', '')}\n\n"
        "### True Evaluation Score (Must Justify This) ###\n"
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
    datasets = [
        {"label": meta["label"], "value": ds_id}
        for ds_id, meta in distill_cfg.TRAINING_DATASETS.items()
    ]
    return {
        "teacher_models": model_config_service.get_select_options(
            usage="distillation_teacher",
            types=["api"],
        ),
        "training_datasets": datasets,
        "default_training_dataset": _LP_PARAM_DATASET,
        "default_instruction": _default_instruction(),
    }


def generate_distillation_dataset(
    teacher_model: str,
    training_dataset: str,
    instruction: str,
) -> dict[str, Any]:
    """生成蒸馏用 CoT 轨迹（同步，无 SSE）。"""
    from app.services.distillation_generation import run_generation

    return run_generation(teacher_model, training_dataset, instruction)


def save_distillation_finetune_dataset(
    teacher_model: str,
    training_dataset: str,
    samples: list[dict[str, Any]],
) -> dict[str, Any]:
    """保存用户校对后的 CoT 样本为 LoRA 微调 JSONL。"""
    if not samples:
        raise ValueError("保存样本列表不能为空")
    if training_dataset not in distill_cfg.TRAINING_DATASETS:
        raise ValueError(f"不支持的数据集: {training_dataset}")

    run_timestamp = distill_cfg.generation_timestamp_slug()
    out_path = distill_cfg.finetune_output_jsonl(
        training_dataset, teacher_model, run_timestamp=run_timestamp
    )
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

    return {
        "success": True,
        "saved_count": len(records),
        "saved_ids": saved_ids,
        "teacher_model": teacher_model,
        "training_dataset": training_dataset,
        "save_path": str(out_path),
        "run_timestamp": run_timestamp,
        "message": f"已保存 {len(records)} 条校对数据至 {out_path.name}，可用于 LoRA 微调",
    }
