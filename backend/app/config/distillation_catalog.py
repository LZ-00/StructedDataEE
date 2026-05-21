"""蒸馏数据集与 CoT 生成配置（参考 DSE generate_cot_dataset / generate_finetune_dataset）。"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

_DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "distillation"
OUTPUT_DIR = _DATA_DIR / "generated"

# 可选：指向 DSE 工程 data/processed_data，用于复用已有 CSV
_DSE_DATA_ROOT = Path(os.getenv("DSE_DATA_ROOT", "")).expanduser()

LP_PARAM_DATASET_ID = "lp-param"

# 返回前端的预览样本上限（仅影响 UI 展示条数，不限制 API 生成）
COT_UI_PREVIEW_MAX_ROWS = int(os.getenv("COT_UI_PREVIEW_MAX_ROWS", "0"))
COT_API_MAX_TOKENS = int(os.getenv("COT_API_MAX_TOKENS", "2000"))
COT_API_MAX_RETRIES = int(os.getenv("COT_API_MAX_RETRIES", "2"))
COT_API_RETRY_DELAY_SEC = float(os.getenv("COT_API_RETRY_DELAY_SEC", "2"))
COT_API_CALL_DELAY_SEC = float(os.getenv("COT_API_CALL_DELAY_SEC", "0.5"))

TRAINING_DATASETS: dict[str, dict[str, str]] = {
    LP_PARAM_DATASET_ID: {
        "label": "工艺参数规范库 (LP-ParamBank)",
        "csv": "lp_param_bank.csv",
        "description": "激光焊接工艺参数与缺陷关系抽取评测集",
    },
}


def dataset_csv_path(dataset_id: str) -> Path:
    meta = TRAINING_DATASETS.get(dataset_id)
    if not meta:
        raise ValueError(f"未知训练数据集: {dataset_id}")

    bundled = _DATA_DIR / meta["csv"]
    if bundled.is_file():
        return bundled

    if _DSE_DATA_ROOT.is_dir():
        override = os.getenv(f"COT_CSV_{dataset_id.upper().replace('-', '_')}", "")
        if override:
            candidate = _DSE_DATA_ROOT / override
            if candidate.is_file():
                return candidate
        fallback = _DSE_DATA_ROOT / "processed_data" / "bc5cdr_origin.csv"
        if fallback.is_file():
            return fallback

    return bundled


def generation_timestamp_slug() -> str:
    """单次生成/保存任务的时间戳后缀（UTC）。"""
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def cot_output_jsonl(
    dataset_id: str,
    teacher_registry_id: str,
    *,
    run_timestamp: str | None = None,
) -> Path:
    """每次生成写入新文件，避免覆盖历史 CoT 与并发追加重复 index。"""
    safe_teacher = teacher_registry_id.replace("/", "_").replace(".", "_")
    ts = run_timestamp or generation_timestamp_slug()
    return OUTPUT_DIR / f"cot_{dataset_id}_{safe_teacher}_{ts}.jsonl"


def finetune_output_jsonl(
    dataset_id: str,
    teacher_registry_id: str,
    *,
    run_timestamp: str | None = None,
) -> Path:
    """校对保存后的 LoRA 微调 JSONL（Instruction / Input / Output）。"""
    safe_teacher = teacher_registry_id.replace("/", "_").replace(".", "_")
    ts = run_timestamp or generation_timestamp_slug()
    return OUTPUT_DIR / f"finetune_{dataset_id}_{safe_teacher}_{ts}.jsonl"


def list_cot_jsonl_for_teacher(dataset_id: str, teacher_registry_id: str) -> list[Path]:
    """按修改时间降序列出某教师在某数据集下的 CoT 产物。"""
    if not OUTPUT_DIR.is_dir():
        return []
    safe_teacher = teacher_registry_id.replace("/", "_").replace(".", "_")
    pattern = f"cot_{dataset_id}_{safe_teacher}_*.jsonl"
    return sorted(OUTPUT_DIR.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
