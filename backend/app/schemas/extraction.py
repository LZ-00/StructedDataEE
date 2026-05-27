"""结构化抽取流水线 API 契约。"""

from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, field_validator

# 激光焊接工艺参数 + 力学性能指标（与任务描述一致）
SCHEMA_FIELDS = (
    "welding_power",
    "welding_speed",
    "defocusing_distance",
    "shielding_gas",
    "shielding_gas_flow_rate",
    "tensile_strength",
    "yield_strength",
    "elongation_rate",
)


class TextChunk(BaseModel):
    chunk_id: str
    text: str
    start_offset: int = 0
    end_offset: int = 0
    document_name: Optional[str] = None
    chapter: Optional[str] = None
    paragraph_index: int = 0
    language: str = "mixed"
    token_count: int = 0


class RelevanceResult(BaseModel):
    is_relevant: bool
    reason: Optional[str] = None


class MaterialRecord(BaseModel):
    """单条激光焊接实验记录的结构化字段。"""

    welding_power: Optional[str] = None
    welding_speed: Optional[str] = None
    defocusing_distance: Optional[str] = None
    shielding_gas: Optional[str] = None
    shielding_gas_flow_rate: Optional[str] = None
    tensile_strength: Optional[str] = None
    yield_strength: Optional[str] = None
    elongation_rate: Optional[str] = None
    # 跨 chunk 关联元信息（MVP）
    record_kind: Literal["complete", "process_only", "mechanics_only", "merged"] = "complete"
    source_chunk_ids: list[str] = Field(default_factory=list)
    merge_note: Optional[str] = None

    @field_validator(*SCHEMA_FIELDS, mode="before")
    @classmethod
    def _coerce_string_fields(cls, value: Any) -> str | None:
        from app.services.extraction.record_parser import coerce_scalar_to_optional_str

        return coerce_scalar_to_optional_str(value)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MaterialRecord:
        from app.services.extraction.record_parser import normalize_record

        return cls.model_validate(normalize_record(data))


class ExtractionItem(BaseModel):
    chunk_id: str
    source_text: str
    relevance: RelevanceResult
    records: list[MaterialRecord] = Field(default_factory=list)
    error: Optional[str] = None


class DocumentMeta(BaseModel):
    filename: Optional[str] = None
    total_chars: int = 0
    chunk_count: int = 0
    relevant_count: int = 0
    warnings: list[str] = Field(default_factory=list)


class DocumentExtractionResponse(BaseModel):
    document_meta: DocumentMeta
    items: list[ExtractionItem] = Field(default_factory=list)
    records: list[MaterialRecord] = Field(default_factory=list)

    def model_dump(self, **kwargs: Any) -> dict[str, Any]:
        data = super().model_dump(**kwargs)
        data["records"] = [
            r.model_dump() if isinstance(r, MaterialRecord) else r for r in self.records
        ]
        return data


class PipelineDefaults(BaseModel):
    max_chunk_chars: int = 1200
    min_chunk_chars: int = 80
    max_chunks: int = 80
    min_chunk_tokens: int = 800
    max_chunk_tokens: int = 1200
    similarity_threshold: float = 0.55
    similarity_drop_delta: float = 0.15
    llm_concurrency: int = 3
    embedding_model: str = "BAAI/bge-m3"
    embedding_cache_dir: str = "/data/lz/modelscope/embedding"
