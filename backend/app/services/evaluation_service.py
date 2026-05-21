"""数据质量评估配置（推理流式逻辑见 evaluation_generation）。"""

from __future__ import annotations

from typing import Any

from app.config import evaluation_catalog as eval_cfg
from app.services import evaluation_benchmark, model_config_service


def get_evaluation_options() -> dict[str, Any]:
    meta = eval_cfg.BENCHMARK_DATASETS[eval_cfg.LP_PARAM_BENCHMARK_ID]
    sample_count = 10
    try:
        samples = evaluation_benchmark.load_benchmark_samples(eval_cfg.LP_PARAM_BENCHMARK_ID)
        sample_count = len(samples)
        example_log = _sample_cot_example(samples[0])
    except Exception:
        example_log = _fallback_example_cot_log()

    return {
        "models": model_config_service.get_select_options(usage="evaluation"),
        "ground_truths": [
            {
                "label": meta["label"],
                "value": eval_cfg.LP_PARAM_BENCHMARK_ID,
            }
        ],
        "default_ground_truth": eval_cfg.LP_PARAM_BENCHMARK_ID,
        "step_descriptions": [
            "对齐焊接工艺抽取结果与标准答案",
            "验证工艺参数、材料与缺陷关系的正确性",
            "诊断错误并分析工艺成因",
            "统合评估结果并计算 RMSE / 精确匹配率",
        ],
        "example_cot_log": example_log,
        "benchmark_sample_count": sample_count,
    }


def _fallback_example_cot_log() -> str:
    return (
        "Step 1: Parse each relation from the AI Prediction sequentially.\n"
        "Step 2: Cross-reference predictions against the Gold Standard.\n"
        "Step 3: Classify each prediction as Correct or Incorrect.\n"
        "Step 4: Reconcile the diagnosis with the final score.\n"
        '{"correctly_predicted_relations": 1, "total_predicted_relations": 1}'
    )


def _sample_cot_example(sample: dict[str, Any]) -> str:
    passage = (sample.get("passage") or "")[:80]
    return (
        f"Step 1: Parse relations from AI Prediction for: {passage}…\n"
        "Step 2: Cross-reference against Gold Standard.\n"
        "Step 3: Classify each prediction.\n"
        "Step 4: Reconcile with the derived score.\n"
        '{"correctly_predicted_relations": '
        f'{sample.get("true_correct", 0)}, "total_predicted_relations": {sample.get("true_total", 0)}}}'
    )
