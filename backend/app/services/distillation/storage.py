"""蒸馏/微调数据文件管理。"""

from __future__ import annotations

import csv
import io
import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from app.config import distillation_catalog as distill_cfg
from app.timezone_utils import ASIA_SHANGHAI, slug_now_asia_shanghai

TRAINING_CSV_FIELDS: tuple[str, ...] = (
    "passage",
    "ai_predicted_relations",
    "true_correct",
    "true_total",
)

_UPLOADS_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "distillation" / "uploads"
_GENERATED_DIR = distill_cfg.OUTPUT_DIR
_SAFE_NAME_RE = re.compile(r"[^a-zA-Z0-9_-]+")


@dataclass
class UploadedDatasetMeta:
    dataset_id: str
    label: str
    path: Path
    modified_at: str


def _safe_slug(name: str) -> str:
    cleaned = _SAFE_NAME_RE.sub("-", (name or "").strip())
    cleaned = cleaned.strip("-").lower()
    return cleaned or "dataset"


def dataset_file_slug(dataset_id: str) -> str:
    return _safe_slug(dataset_id.replace(":", "-").replace("/", "-"))


def training_template_csv() -> str:
    return ",".join(TRAINING_CSV_FIELDS) + "\n"


def _decode_csv_bytes(raw: bytes) -> str:
    for enc in ("utf-8-sig", "utf-8", "gbk"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    raise ValueError("CSV 文件编码无法识别，请使用 UTF-8 编码后重试")


def validate_training_csv_content(raw: bytes) -> list[dict[str, str]]:
    text = _decode_csv_bytes(raw)
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise ValueError("CSV 文件缺少表头")
    headers = tuple(h.strip() for h in reader.fieldnames)
    if headers != TRAINING_CSV_FIELDS:
        expected = ",".join(TRAINING_CSV_FIELDS)
        actual = ",".join(headers)
        raise ValueError(
            f"CSV 表头不符合要求。期望: {expected}；实际: {actual}"
        )
    rows: list[dict[str, str]] = []
    for row in reader:
        rows.append({k: (row.get(k) or "").strip() for k in TRAINING_CSV_FIELDS})
    return rows


def save_uploaded_training_csv(filename: str, raw: bytes) -> UploadedDatasetMeta:
    rows = validate_training_csv_content(raw)
    if not rows:
        raise ValueError("上传 CSV 不能为空")
    stem = _safe_slug(Path(filename or "dataset").stem)
    ts = slug_now_asia_shanghai()
    saved_name = f"uploaded_{stem}_{ts}.csv"
    _UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    path = _UPLOADS_DIR / saved_name
    path.write_text(_decode_csv_bytes(raw), encoding="utf-8")
    modified = datetime.fromtimestamp(path.stat().st_mtime, tz=ASIA_SHANGHAI).isoformat()
    ds_id = f"upload-{stem}_{ts.lower()}"
    return UploadedDatasetMeta(
        dataset_id=ds_id,
        label=f"上传数据集 {ts}",
        path=path,
        modified_at=modified,
    )


def list_uploaded_training_datasets() -> list[UploadedDatasetMeta]:
    if not _UPLOADS_DIR.is_dir():
        return []
    items: list[UploadedDatasetMeta] = []
    for path in sorted(_UPLOADS_DIR.glob("uploaded_*.csv"), key=lambda p: p.stat().st_mtime, reverse=True):
        stem = path.stem
        suffix = stem.replace("uploaded_", "", 1)
        ds_id = f"upload-{suffix.lower()}"
        modified = datetime.fromtimestamp(path.stat().st_mtime, tz=ASIA_SHANGHAI).isoformat()
        stamp_match = re.search(r"(\d{8}_\d{6})$", path.stem)
        label = f"上传数据集 {stamp_match.group(1)}" if stamp_match else "上传数据集"
        items.append(
            UploadedDatasetMeta(
                dataset_id=ds_id,
                label=label,
                path=path,
                modified_at=modified,
            )
        )
    return items


def resolve_training_dataset_path(dataset_id: str) -> Path:
    if dataset_id in distill_cfg.TRAINING_DATASETS:
        return distill_cfg.dataset_csv_path(dataset_id)
    for item in list_uploaded_training_datasets():
        if item.dataset_id == dataset_id:
            return item.path
    raise ValueError(f"不支持的数据集: {dataset_id}")


def build_training_dataset_options() -> tuple[list[dict[str, str]], str]:
    options: list[dict[str, str]] = []
    for ds_id, meta in distill_cfg.TRAINING_DATASETS.items():
        options.append({"label": meta["label"], "value": ds_id})
    for item in list_uploaded_training_datasets():
        options.append({"label": item.label, "value": item.dataset_id})
    default_value = distill_cfg.LP_PARAM_DATASET_ID
    return options, default_value


def list_finetune_jsonl_candidates() -> list[Path]:
    if not _GENERATED_DIR.is_dir():
        return []
    return sorted(
        _GENERATED_DIR.glob("finetune_*.jsonl"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )


def _count_jsonl_lines(path: Path) -> int:
    count = 0
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                count += 1
    return count


def summarize_finetune_dataset(path: Path) -> dict[str, Any]:
    mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=ASIA_SHANGHAI).isoformat()
    return {
        "path": str(path.resolve()),
        "filename": path.name,
        "source": "distillation_saved",
        "sample_count": _count_jsonl_lines(path),
        "modified_at": mtime,
    }


def list_recent_finetune_datasets(limit: int = 3) -> list[dict[str, Any]]:
    return [summarize_finetune_dataset(p) for p in list_finetune_jsonl_candidates()[:limit]]


def prune_finetune_datasets(limit: int = 3) -> list[str]:
    candidates = list_finetune_jsonl_candidates()
    removed: list[str] = []
    for obsolete in candidates[limit:]:
        obsolete.unlink(missing_ok=True)
        removed.append(obsolete.name)
    return removed


def validate_finetune_jsonl(raw: bytes) -> int:
    text = raw.decode("utf-8")
    count = 0
    for idx, line in enumerate(text.splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"JSONL 第 {idx} 行不是合法 JSON: {exc}") from exc
        for key in ("Instruction", "Input", "Output"):
            if key not in data:
                raise ValueError(f"JSONL 第 {idx} 行缺少字段: {key}")
        count += 1
    if count == 0:
        raise ValueError("上传 JSONL 为空")
    return count


def save_uploaded_finetune_jsonl(filename: str, raw: bytes) -> dict[str, Any]:
    sample_count = validate_finetune_jsonl(raw)
    stem = _safe_slug(Path(filename or "finetune").stem)
    ts = slug_now_asia_shanghai()
    saved_name = f"finetune_upload_{stem}_{ts}.jsonl"
    _GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    path = _GENERATED_DIR / saved_name
    path.write_bytes(raw)
    removed = prune_finetune_datasets(limit=3)
    return {
        "success": True,
        "dataset": summarize_finetune_dataset(path),
        "sample_count": sample_count,
        "removed": removed,
        "message": f"上传成功，当前保留最新 3 条微调数据记录",
    }
