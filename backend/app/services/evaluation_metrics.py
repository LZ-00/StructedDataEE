"""评估指标（参考 DSE utils/eval.py 与 finetuning/finetune.py ModelEvaluator）。"""

from __future__ import annotations

import json
import math
import re
from typing import Any, Optional


def calculate_exact_match(
    llm_correct: int,
    llm_total: int,
    gold_correct: int,
    gold_total: int,
) -> int:
    if llm_correct == gold_correct and llm_total == gold_total:
        return 1
    return 0


def calculate_mse(
    llm_correct: int,
    llm_total: int,
    gold_correct: int,
    gold_total: int,
) -> float:
    return ((llm_correct - gold_correct) ** 2 + (llm_total - gold_total) ** 2) / 2.0


def aggregate_metrics(
    exact_matches: list[int],
    mse_values: list[float],
) -> dict[str, Any]:
    avg_exact_match = sum(exact_matches) / len(exact_matches) if exact_matches else 0.0
    mean_mse: Optional[float] = (
        sum(mse_values) / len(mse_values) if mse_values else None
    )
    rmse: Optional[float] = (
        math.sqrt(mean_mse) if mean_mse is not None else None
    )
    return {
        "exact_match": avg_exact_match,
        "mean_mse": mean_mse,
        "rmse": rmse,
        "total_samples": len(exact_matches),
        "successful_samples": len(exact_matches),
    }


def extract_score_json(output: str) -> Optional[dict[str, int]]:
    """从模型输出中解析评分 JSON（参考 DSE OutputParser.extract_json_from_output）。"""
    if not output or not output.strip():
        return None

    text = output.strip()
    lines = text.split("\n")
    for line in reversed(lines):
        line = line.strip()
        if line.startswith("{") and line.endswith("}"):
            try:
                result = json.loads(line)
                if _is_score_dict(result):
                    return _normalize_score_dict(result)
            except json.JSONDecodeError:
                pass

    pattern = (
        r'\{[^{}]*(?:"correctly_predicted_relations"[^{}]*"total_predicted_relations"'
        r'|"total_predicted_relations"[^{}]*"correctly_predicted_relations")[^{}]*\}'
    )
    matches = list(re.finditer(pattern, text, re.DOTALL))
    if matches:
        try:
            result = json.loads(matches[-1].group(0))
            if _is_score_dict(result):
                return _normalize_score_dict(result)
        except json.JSONDecodeError:
            pass

    brace_count = 0
    start_idx = -1
    for i in range(len(text) - 1, -1, -1):
        if text[i] == "}":
            if brace_count == 0:
                start_idx = i
            brace_count += 1
        elif text[i] == "{":
            brace_count -= 1
            if brace_count == 0 and start_idx != -1:
                chunk = text[i : start_idx + 1]
                try:
                    result = json.loads(chunk)
                    if _is_score_dict(result):
                        return _normalize_score_dict(result)
                except (json.JSONDecodeError, ValueError):
                    pass
                start_idx = -1
                brace_count = 0

    try:
        result = json.loads(text)
        if _is_score_dict(result):
            return _normalize_score_dict(result)
    except json.JSONDecodeError:
        pass

    return None


def _is_score_dict(obj: Any) -> bool:
    return (
        isinstance(obj, dict)
        and "correctly_predicted_relations" in obj
        and "total_predicted_relations" in obj
    )


def _normalize_score_dict(result: dict[str, Any]) -> dict[str, int]:
    return {
        "correctly_predicted_relations": int(result["correctly_predicted_relations"]),
        "total_predicted_relations": int(result["total_predicted_relations"]),
    }
