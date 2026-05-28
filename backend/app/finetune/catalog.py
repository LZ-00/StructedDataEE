"""LoRA 微调路径与流程配置。"""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Any

from app.services.distillation.storage import list_recent_finetune_datasets
from app.timezone_utils import ASIA_SHANGHAI

_DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "finetune"
# 软著 Web 微调权重目录（DSE finetuning_output 下独立子目录）
_DEFAULT_FINETUNE_OUTPUT = "/data/lz/FineTuning/DSE/finetuning_output/ruanzhu"
FINETUNE_OUTPUT_DIR = Path(
    os.getenv("FINETUNE_OUTPUT_DIR", _DEFAULT_FINETUNE_OUTPUT)
).expanduser()
BUNDLED_DATASET = _DATA_DIR / "finetune_dataset.jsonl"
INSTRUCTION_FILE = _DATA_DIR / "finetune_instruction.txt"
_GENERATED_DIR = _DATA_DIR.parent / "distillation" / "generated"

_DSE_ROOT = Path(os.getenv("DSE_DATA_ROOT", "")).expanduser()

# auto: 无 torch/peft/CUDA 时用演示；0: 强制真实训练；1: 强制演示
FINETUNE_FORCE_DEMO = os.getenv("FINETUNE_FORCE_DEMO", "auto").strip().lower()
FINETUNE_MAX_SAMPLES = int(os.getenv("FINETUNE_MAX_SAMPLES", "0"))
FINETUNE_MAX_LENGTH = int(os.getenv("FINETUNE_MAX_LENGTH", "2048"))

FINETUNE_STEPS = [
    {"title": "准备训练数据", "description": "加载最新 finetune_*.jsonl"},
    {"title": "加载基座模型", "description": "从 ModelScope 本地权重加载"},
    {"title": "配置 LoRA", "description": "注入低秩适配器 (PEFT)"},
    {"title": "LoRA 微调", "description": "HuggingFace Trainer 训练"},
    {"title": "保存权重", "description": "写入 finetuning_output/ruanzhu"},
]


def finetune_output_base() -> Path:
    """LoRA 权重根目录。"""
    return FINETUNE_OUTPUT_DIR


def _count_jsonl_lines(path: Path) -> int:
    if not path.is_file():
        return 0
    count = 0
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                count += 1
    return count


def list_finetune_jsonl_candidates() -> list[Path]:
    """蒸馏保存的 finetune_*.jsonl，按修改时间降序。"""
    if not _GENERATED_DIR.is_dir():
        return []
    return sorted(
        _GENERATED_DIR.glob("finetune_*.jsonl"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )


def describe_finetune_dataset() -> dict[str, Any]:
    """描述本次微调将使用的数据集（供 options 与训练日志）。"""
    recent = list_recent_finetune_datasets(limit=3)
    if recent:
        first = dict(recent[0])
        first["candidate_count"] = len(list_finetune_jsonl_candidates())
        return first

    if BUNDLED_DATASET.is_file():
        mtime = BUNDLED_DATASET.stat().st_mtime
        return {
            "path": str(BUNDLED_DATASET.resolve()),
            "filename": BUNDLED_DATASET.name,
            "source": "bundled",
            "sample_count": _count_jsonl_lines(BUNDLED_DATASET),
            "modified_at": datetime.fromtimestamp(mtime, tz=ASIA_SHANGHAI).isoformat(),
            "candidate_count": 0,
        }

    if _DSE_ROOT.is_dir():
        dse_path = _DSE_ROOT / "data" / "processed_data" / "finetune_dataset.jsonl"
        if dse_path.is_file():
            mtime = dse_path.stat().st_mtime
            return {
                "path": str(dse_path.resolve()),
                "filename": dse_path.name,
                "source": "dse",
                "sample_count": _count_jsonl_lines(dse_path),
                "modified_at": datetime.fromtimestamp(mtime, tz=ASIA_SHANGHAI).isoformat(),
                "candidate_count": 0,
            }

    return {
        "path": "",
        "filename": "",
        "source": "missing",
        "sample_count": 0,
        "modified_at": "",
        "candidate_count": 0,
    }


def resolve_finetune_dataset_path(training_dataset_path: str = "") -> Path:
    """每次训练调用：优先使用修改时间最新的 finetune_*.jsonl。"""
    if training_dataset_path:
        selected = Path(training_dataset_path)
        if selected.is_file():
            return selected
        raise FileNotFoundError(f"指定训练数据不存在: {training_dataset_path}")
    info = describe_finetune_dataset()
    path_str = info.get("path") or ""
    if path_str:
        return Path(path_str)
    return BUNDLED_DATASET


def checkpoint_dir(run_id: str) -> Path:
    """单次微调输出目录：ruanzhu/{run_id}，adapter 直接写在目录根下。"""
    return finetune_output_base() / run_id
