"""文本块与任务描述的相关性判断。"""

from __future__ import annotations

from app.data.prompt import build_relevance_prompt
from app.schemas.extraction import RelevanceResult, TextChunk
from app.services.extraction.llm_gateway import invoke_registered_model, resolve_model_id
from app.services.extraction.record_parser import parse_relevance_json


def assess_relevance(
    chunk: TextChunk,
    task_description: str,
    model: str,
) -> RelevanceResult:
    registry_id = resolve_model_id(model)
    prompt = build_relevance_prompt(chunk.text, task_description)
    raw = invoke_registered_model(registry_id, prompt)
    parsed = parse_relevance_json(raw)
    is_relevant = bool(parsed.get("is_relevant"))
    reason = parsed.get("reason")
    if reason is not None:
        reason = str(reason).strip() or None
    return RelevanceResult(is_relevant=is_relevant, reason=reason)
