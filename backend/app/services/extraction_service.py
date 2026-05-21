"""激光焊接工艺结构化抽取业务逻辑（演示：返回与 demo 一致的结构）。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from app.config import distillation_catalog as distill_cfg
from app.config import evaluation_catalog as eval_cfg
from app.services import cot_generation_service, model_config_service

_EXTRACTION_DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "extraction"
_DEMO_PATH = _EXTRACTION_DATA_DIR / "demo_extraction.json"
_SAMPLE_TEXT_PATH = Path(__file__).with_name("sample_input.txt")
_EN_PASSAGES_PATH = _EXTRACTION_DATA_DIR / "lp_param_extraction_samples_en.json"


def _load_demo() -> dict[str, Any]:
    with open(_DEMO_PATH, encoding="utf-8") as f:
        return json.load(f)


_ENTITY_KEYS = ("text", "type", "start", "end")
_RELATION_KEYS = ("type", "source", "sourceType", "target", "targetType", "evidence")


def _pick_fields(item: dict[str, Any], allowed: tuple[str, ...]) -> dict[str, Any]:
    return {k: item[k] for k in allowed if k in item}


def _normalize_extraction_result(data: dict[str, Any]) -> dict[str, Any]:
    """仅保留 document_id、entities、relations（不含 confidence 等扩展字段）。"""
    entities = [
        _pick_fields(e, _ENTITY_KEYS)
        for e in (data.get("entities") or [])
        if isinstance(e, dict)
    ]
    relations = [
        _pick_fields(r, _RELATION_KEYS)
        for r in (data.get("relations") or [])
        if isinstance(r, dict)
    ]
    return {
        "document_id": data.get("document_id", ""),
        "entities": entities,
        "relations": relations,
    }


def _load_en_passages() -> list[str]:
    if not _EN_PASSAGES_PATH.is_file():
        return []
    with open(_EN_PASSAGES_PATH, encoding="utf-8") as f:
        payload = json.load(f)
    passages = payload.get("passages_en") or []
    return [str(p).strip() for p in passages if str(p).strip()]


def _load_lp_param_samples() -> list[dict[str, str]]:
    """与 lp_param_bank.csv / lp_param_benchmark.jsonl 对齐的英文样本列表。"""
    csv_path = distill_cfg.dataset_csv_path(eval_cfg.LP_PARAM_BENCHMARK_ID)
    rows = cot_generation_service.load_csv_rows(csv_path)
    en_passages = _load_en_passages()
    samples: list[dict[str, str]] = []
    for idx, row in enumerate(rows):
        passage_en = en_passages[idx] if idx < len(en_passages) else row.get("passage", "")
        samples.append(
            {
                "passage": passage_en,
                "passage_zh": row.get("passage", ""),
                "gold_relations": row.get("gold_relations", ""),
                "ai_predicted_relations": row.get("ai_predicted_relations", ""),
            }
        )
    return samples


_DEFAULT_SAMPLE_PARAGRAPHS = 3


def _default_sample_text() -> str:
    samples = _load_lp_param_samples()
    if samples:
        paragraphs = [s["passage"] for s in samples[:_DEFAULT_SAMPLE_PARAGRAPHS]]
        return "\n\n".join(p for p in paragraphs if p)
    if _SAMPLE_TEXT_PATH.is_file():
        return _SAMPLE_TEXT_PATH.read_text(encoding="utf-8").strip()
    return ""


def get_workspace_options() -> dict[str, Any]:
    """抽取工作台配置：模型列表、默认任务描述与示例文本。"""
    samples = _load_lp_param_samples()
    models = model_config_service.get_select_options(usage="extraction")
    return {
        "models": models,
        "default_model": model_config_service.get_default_model_id("extraction"),
        "default_task_description": (
            "Extract base materials, process parameters (power, speed, shielding gas, etc.), "
            "and associated weld defects or quality outcomes from laser welding process reports"
        ),
        "sample_text": _default_sample_text(),
        "sample_texts": [s["passage"] for s in samples],
        "benchmark_source": "lp_param_bank.csv",
    }


def run_extraction(source_text: str, model: str, task_description: str) -> dict[str, Any]:
    """
    执行抽取管线占位实现：校验非空文本后返回结构化结果。
    生产环境可替换为模型推理、PDF 解析等。
    """
    if not (source_text or "").strip():
        raise ValueError("待抽取文本为空")

    _ = model, task_description  # 演示占位；生产环境用于推理配置
    return _normalize_extraction_result(_load_demo())


def decode_upload_bytes(raw: bytes, filename: Optional[str]) -> str:
    name = (filename or "").lower()
    if name.endswith(".pdf"):
        return raw.decode("utf-8", errors="replace")[:2000] + "\n\n[演示] PDF 二进制已接收，后端可接入解析器提取正文。"
    return raw.decode("utf-8", errors="replace")
