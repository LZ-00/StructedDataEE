import threading

import pytest

from app.schemas.extraction import MaterialRecord, RelevanceResult, TextChunk
from app.services.extraction import pipeline
from app.services.extraction.errors import ExtractionCancelled


def test_run_document_extraction_text_pipeline(monkeypatch):
    chunks = [
        TextChunk(chunk_id="c-001", text="无关描述", start_offset=0, end_offset=4),
        TextChunk(chunk_id="c-002", text="材料A在800C烧结2h", start_offset=5, end_offset=20),
    ]

    monkeypatch.setattr(
        pipeline.semantic_chunker,
        "chunk_text",
        lambda text, defaults=None, document_name=None, cancel_event=None: (chunks, []),
    )

    def fake_rel(chunk, task_description, model):
        if chunk.chunk_id == "c-002":
            return RelevanceResult(is_relevant=True, reason="包含温度与时间")
        return RelevanceResult(is_relevant=False, reason="无字段信息")

    monkeypatch.setattr(pipeline.relevance_filter, "assess_relevance", fake_rel)
    monkeypatch.setattr(
        pipeline.structured_extractor,
        "extract_records",
        lambda source_text, task_description, model: [
            MaterialRecord(
                welding_power="800 W",
                welding_speed="1.2 m/min",
                shielding_gas="Ar",
            )
        ],
    )

    res = pipeline.run_document_extraction(
        source="这是一个测试输入",
        model="local-qwen-7b",
        task_description="抽取材料与工艺参数",
    )

    assert res["document_meta"]["chunk_count"] == 2
    assert res["document_meta"]["relevant_count"] == 1
    assert len(res["items"]) == 1
    assert res["items"][0]["chunk_id"] == "c-002"
    assert len(res["records"]) == 1


def test_run_document_extraction_file_empty_chunks(monkeypatch):
    monkeypatch.setattr(
        pipeline.document_loader,
        "load_document",
        lambda raw, filename: ("文本", []),
    )
    monkeypatch.setattr(
        pipeline.semantic_chunker,
        "chunk_text",
        lambda text, defaults=None, document_name=None, cancel_event=None: ([], ["无法切分"]),
    )

    res = pipeline.run_document_extraction(
        source=b"mock",
        filename="demo.txt",
        model="local-qwen-7b",
        task_description="抽取",
    )

    assert res["document_meta"]["filename"] == "demo.txt"
    assert res["items"] == []
    assert res["records"] == []


def test_run_document_extraction_emits_progress(monkeypatch):
    chunks = [TextChunk(chunk_id="c-001", text="材料B", start_offset=0, end_offset=3)]

    monkeypatch.setattr(
        pipeline.semantic_chunker,
        "chunk_text",
        lambda text, defaults=None, document_name=None, cancel_event=None: (chunks, []),
    )
    monkeypatch.setattr(
        pipeline.relevance_filter,
        "assess_relevance",
        lambda chunk, task_description, model: RelevanceResult(is_relevant=True),
    )
    monkeypatch.setattr(
        pipeline.structured_extractor,
        "extract_records",
        lambda source_text, task_description, model: [
            MaterialRecord(welding_power="2.8 kW", tensile_strength="350 MPa")
        ],
    )

    events: list[dict] = []
    pipeline.run_document_extraction(
        source="测试",
        model="local-qwen-7b",
        task_description="抽取",
        emit=events.append,
    )

    types = [e["type"] for e in events]
    assert "step_init" in types
    assert "chunked" in types
    assert "relevance_done" in types
    assert "item" in types
    assert types[-1] == "done"


def test_run_document_extraction_cancelled_before_relevance(monkeypatch):
    chunks = [
        TextChunk(chunk_id="c-001", text="材料A", start_offset=0, end_offset=3),
        TextChunk(chunk_id="c-002", text="材料B", start_offset=4, end_offset=7),
    ]
    cancel = threading.Event()

    monkeypatch.setattr(
        pipeline.semantic_chunker,
        "chunk_text",
        lambda text, defaults=None, document_name=None, cancel_event=None: (chunks, []),
    )

    def fake_rel(chunk, task_description, model):
        cancel.set()
        return RelevanceResult(is_relevant=True)

    monkeypatch.setattr(pipeline.relevance_filter, "assess_relevance", fake_rel)

    with pytest.raises(ExtractionCancelled):
        pipeline.run_document_extraction(
            source="测试",
            model="local-qwen-7b",
            task_description="抽取",
            cancel_event=cancel,
        )
