"""材料科学文献结构化抽取工作台服务。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from app.config import distillation_catalog as distill_cfg
from app.config import evaluation_catalog as eval_cfg
from app.schemas.extraction import PipelineDefaults
from app.services import cot_generation_service, model_config_service
from app.services.extraction import pipeline
from app.services.extraction.document_loader import load_document

_EXTRACTION_DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "extraction"
_EN_PASSAGES_PATH = _EXTRACTION_DATA_DIR / "lp_param_extraction_samples_en.json"
_SAMPLE_TEXT_PATH = Path(__file__).with_name("sample_input.txt")

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


_DEFAULT_SAMPLE_PARAGRAPHS = 1


def _default_sample_text() -> str:
    samples = _load_lp_param_samples()
    if samples:
        return samples[0]["passage"]
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
            "Identify each laser welding experimental record in the following passage. "
            "For each record, extract the welding process parameters, including welding power (W), "
            "welding speed (m/min), defocusing distance (mm), shielding gas, and shielding gas flow rate(L/min), "
            "together with the corresponding mechanical performance metrics, including tensile strength, "
            "yield strength, and elongation rate (%). "
            "Only extract information explicitly stated in the passage."
        ),
        "sample_text": _default_sample_text(),
        "sample_texts": [s["passage"] for s in samples],
        "benchmark_source": "lp_param_bank.csv",
        "pipeline_defaults": PipelineDefaults().model_dump(),
    }


def run_extraction(source_text: str, model: str, task_description: str) -> dict[str, Any]:
    return pipeline.run_document_extraction(
        source=source_text,
        model=model,
        task_description=task_description,
    )


def run_extraction_from_file(
    raw: bytes,
    filename: Optional[str],
    model: str,
    task_description: str,
) -> dict[str, Any]:
    return pipeline.run_document_extraction(
        source=raw,
        filename=filename,
        model=model,
        task_description=task_description,
    )


def decode_upload_bytes(raw: bytes, filename: Optional[str]) -> str:
    text, _warnings = load_document(raw, filename)
    return text
