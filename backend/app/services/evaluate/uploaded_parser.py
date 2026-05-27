"""上传结构化抽取结果的解析与校验。"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

_WELDING_FIELDS = (
    "welding_power",
    "welding_speed",
    "defocusing_distance",
    "shielding_gas",
    "shielding_gas_flow_rate",
)

_MECHANICAL_FIELDS = (
    "tensile_strength",
    "yield_strength",
    "elongation_rate",
)


@dataclass
class UploadedEvaluationRecord:
    index: int
    record_id: str
    chunk_id: str
    chunk_text: str
    welding_parameters: dict[str, str | None]
    mechanical_performance: dict[str, str | None]


def parse_uploaded_records(raw: bytes, filename: str | None = None) -> list[UploadedEvaluationRecord]:
    if not raw:
        raise ValueError("上传文件为空，请上传结构化抽取结果 JSON")

    try:
        payload = json.loads(raw.decode("utf-8"))
    except UnicodeDecodeError as exc:
        raise ValueError("上传文件不是有效的 UTF-8 JSON") from exc
    except json.JSONDecodeError as exc:
        raise ValueError("上传文件不是合法 JSON") from exc

    records = payload.get("experimental_records")
    if not isinstance(records, list) or not records:
        raise ValueError("上传 JSON 缺少 experimental_records 或为空")

    parsed: list[UploadedEvaluationRecord] = []
    invalid_count = 0
    for idx, item in enumerate(records, start=1):
        if not isinstance(item, dict):
            invalid_count += 1
            continue
        source = item.get("source") or {}
        if not isinstance(source, dict):
            source = {}
        chunk_text = _to_optional_text(source.get("chunk"))
        if not chunk_text:
            invalid_count += 1
            continue

        parsed.append(
            UploadedEvaluationRecord(
                index=idx,
                record_id=_to_optional_text(item.get("record_id")) or f"R{idx:03d}",
                chunk_id=_to_optional_text(source.get("chunk_id")) or f"c-{idx:03d}",
                chunk_text=chunk_text,
                welding_parameters=_extract_fields(item.get("welding_parameters"), _WELDING_FIELDS),
                mechanical_performance=_extract_fields(
                    item.get("mechanical_performance"), _MECHANICAL_FIELDS
                ),
            )
        )

    if not parsed:
        detail = "所有 experimental_records 都缺少 source.chunk"
        if filename:
            detail = f"{filename}: {detail}"
        raise ValueError(detail)

    if invalid_count and invalid_count == len(records):
        raise ValueError("上传 JSON 结构不符合评估要求")

    return parsed


def _extract_fields(raw: Any, fields: tuple[str, ...]) -> dict[str, str | None]:
    data = raw if isinstance(raw, dict) else {}
    return {field: _to_optional_text(data.get(field)) for field in fields}


def _to_optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
