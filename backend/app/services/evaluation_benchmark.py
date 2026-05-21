"""从 lp_param_bank.csv 构建并加载评估基准数据集。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.config import evaluation_catalog as eval_cfg
from app.services import cot_generation_service

_INSTRUCTION_PATH = Path(__file__).with_name("evaluation_instruction.txt")


def _default_instruction() -> str:
    if _INSTRUCTION_PATH.is_file():
        return _INSTRUCTION_PATH.read_text(encoding="utf-8").strip()
    return (
        "Evaluate welding relation extraction. "
        'Output CoT then {"correctly_predicted_relations": N, "total_predicted_relations": M}.'
    )


def build_eval_input(row: dict[str, str]) -> str:
    """评估推理用 Input（不含标准分数，对齐 DSE ddi_dataset.jsonl）。"""
    return (
        "[Task Description]\n"
        "Evaluate welding relation extraction.\n\n"
        f"[Context]\n{row.get('passage', '')}\n\n"
        f"[Gold Standard]\n{row.get('gold_relations', '')}\n\n"
        f"[AI Prediction]\n{row.get('ai_predicted_relations', '')}"
    )


def row_to_benchmark_record(row: dict[str, str], index: int) -> dict[str, Any]:
    try:
        gold_correct = int(row.get("true_correct", "0"))
        gold_total = int(row.get("true_total", "0"))
    except ValueError:
        gold_correct, gold_total = 0, 0
    return {
        "index": index,
        "Instruction": _default_instruction(),
        "Input": build_eval_input(row),
        "true_correct": gold_correct,
        "true_total": gold_total,
        "passage": row.get("passage", ""),
        "gold_relations": row.get("gold_relations", ""),
        "ai_predicted_relations": row.get("ai_predicted_relations", ""),
    }


def ensure_benchmark_jsonl() -> Path:
    """若基准 JSONL 不存在或源 CSV 更新，则从 lp_param_bank.csv 重新生成。"""
    from app.config import distillation_catalog as distill_cfg

    out_path = eval_cfg.BENCHMARK_JSONL
    csv_path = distill_cfg.dataset_csv_path(eval_cfg.LP_PARAM_BENCHMARK_ID)
    if not csv_path.is_file():
        raise FileNotFoundError(f"评估源 CSV 不存在: {csv_path}")

    csv_mtime = csv_path.stat().st_mtime
    if out_path.is_file() and out_path.stat().st_mtime >= csv_mtime:
        return out_path

    rows = cot_generation_service.load_csv_rows(csv_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        for idx, row in enumerate(rows, start=1):
            f.write(json.dumps(row_to_benchmark_record(row, idx), ensure_ascii=False) + "\n")
    return out_path


def load_benchmark_samples(benchmark_id: str) -> list[dict[str, Any]]:
    if benchmark_id not in eval_cfg.BENCHMARK_DATASETS:
        raise ValueError(f"未知评估基准: {benchmark_id}")
    path = ensure_benchmark_jsonl()
    samples: list[dict[str, Any]] = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                samples.append(json.loads(line))
    if not samples:
        raise ValueError(f"评估基准为空: {path}")
    return samples
