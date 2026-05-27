"""对相关文本段执行结构化字段抽取。"""

from __future__ import annotations

from app.data.prompt import build_extraction_prompt
from app.schemas.extraction import MaterialRecord
from app.services.extraction.llm_gateway import invoke_registered_model, resolve_model_id
from app.services.extraction.record_parser import parse_extraction_records


def extract_records(
    source_text: str,
    task_description: str,
    model: str,
) -> list[MaterialRecord]:
    paragraph = (source_text or "").strip()
    if not paragraph:
        return []
    registry_id = resolve_model_id(model)
    prompt = build_extraction_prompt(paragraph, task_description)
    raw = invoke_registered_model(registry_id, prompt)
    return parse_extraction_records(raw)
