"""抽取结果 JSON 解析与字段归一化。"""

from __future__ import annotations

import json
import re
from typing import Any

from app.schemas.extraction import SCHEMA_FIELDS, MaterialRecord


def strip_json_fence(text: str) -> str:
    raw = (text or "").strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", raw, re.IGNORECASE)
    if fence:
        return fence.group(1).strip()
    return raw


def coerce_scalar_to_optional_str(value: Any) -> str | None:
    """
    将 LLM 输出的多种标量类型统一为 Optional[str]。
    兼容 int/float/bool/数字字符串，避免 Pydantic string_type 校验失败。
    """
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if value.is_integer():
            return str(int(value))
        return format(value, "g")
    if isinstance(value, str):
        text = value.strip()
        return text or None
    if isinstance(value, (list, tuple)):
        parts: list[str] = []
        for item in value:
            coerced = coerce_scalar_to_optional_str(item)
            if coerced:
                parts.append(coerced)
        return ", ".join(parts) if parts else None
    if isinstance(value, dict):
        try:
            text = json.dumps(value, ensure_ascii=False)
        except (TypeError, ValueError):
            text = str(value)
        text = text.strip()
        return text or None
    text = str(value).strip()
    return text or None


def normalize_record(item: Any) -> dict[str, Any]:
    if not isinstance(item, dict):
        return {field: None for field in SCHEMA_FIELDS}
    return {field: coerce_scalar_to_optional_str(item.get(field)) for field in SCHEMA_FIELDS}


def parse_extraction_records(raw_output: str) -> list[MaterialRecord]:
    cleaned = strip_json_fence(raw_output)
    if not cleaned:
        raise ValueError("模型未返回有效内容")

    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("[")
        end = cleaned.rfind("]")
        if start == -1 or end == -1 or end <= start:
            raise ValueError("模型输出不是合法 JSON") from None
        parsed = json.loads(cleaned[start : end + 1])

    if isinstance(parsed, dict):
        parsed = [parsed]
    if not isinstance(parsed, list):
        raise ValueError("模型输出应为 JSON 数组")

    return [MaterialRecord.from_dict(normalize_record(item)) for item in parsed]


def parse_relevance_json(raw_output: str) -> dict[str, Any]:
    cleaned = strip_json_fence(raw_output)
    if not cleaned:
        raise ValueError("模型未返回有效内容")
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise ValueError("模型输出不是合法 JSON") from None
        parsed = json.loads(cleaned[start : end + 1])
    if not isinstance(parsed, dict):
        raise ValueError("相关性判断输出应为 JSON 对象")
    return parsed
