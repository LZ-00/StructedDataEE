"""思维链评估基准数据集配置（源自 lp_param_bank.csv）。"""

from __future__ import annotations

from pathlib import Path

from app.config import distillation_catalog as distill_cfg

LP_PARAM_BENCHMARK_ID = distill_cfg.LP_PARAM_DATASET_ID

_BENCHMARK_DIR = Path(__file__).resolve().parent.parent / "data" / "evaluation"
BENCHMARK_JSONL = _BENCHMARK_DIR / "lp_param_benchmark.jsonl"

BENCHMARK_DATASETS: dict[str, dict[str, str]] = {
    LP_PARAM_BENCHMARK_ID: {
        "label": "工艺参数规范库评估基准 (LP-ParamBank)",
        "description": "激光焊接工艺参数与缺陷关系抽取评测集（10 条）",
        "source_csv": "lp_param_bank.csv",
    },
}
