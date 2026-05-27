from app.schemas.extraction import ExtractionItem, MaterialRecord, RelevanceResult, TextChunk
from app.services.extraction.record_merger import merge_records


def _mk_item(chunk_id: str, text: str, records: list[MaterialRecord]) -> ExtractionItem:
    return ExtractionItem(
        chunk_id=chunk_id,
        source_text=text,
        relevance=RelevanceResult(is_relevant=True, reason=None),
        records=records,
    )


def test_merge_process_and_mechanics_across_neighbor_chunks():
    chunks = [
        TextChunk(chunk_id="c-001", text="工艺参数段", chapter="3.1 工艺参数"),
        TextChunk(chunk_id="c-002", text="力学性能段", chapter="3.1 工艺参数"),
    ]
    items = [
        _mk_item(
            "c-001",
            "Laser power 2.8 kW, welding speed 1.2 m/min, shielding gas Ar.",
            [MaterialRecord(welding_power="2.8 kW", welding_speed="1.2 m/min", shielding_gas="Ar")],
        ),
        _mk_item(
            "c-002",
            "The joint shows tensile strength 350 MPa and elongation rate 14%.",
            [MaterialRecord(tensile_strength="350 MPa", elongation_rate="14%")],
        ),
    ]

    merged_items, merged_records, stats = merge_records(chunks, items)

    assert stats.merged_count == 1
    assert stats.unmatched_count == 0
    assert len(merged_records) == 1
    merged = merged_records[0]
    assert merged.record_kind == "merged"
    assert merged.welding_power == "2.8 kW"
    assert merged.tensile_strength == "350 MPa"
    assert merged.source_chunk_ids == ["c-001", "c-002"]
    assert any(i.chunk_id == "c-001" and len(i.records) == 1 for i in merged_items)


def test_keep_unmatched_records_with_kind_and_note():
    chunks = [TextChunk(chunk_id="c-003", text="仅工艺"), TextChunk(chunk_id="c-010", text="远距离性能")]
    items = [
        _mk_item("c-003", "Power 3.0 kW", [MaterialRecord(welding_power="3.0 kW")]),
        _mk_item("c-010", "Yield 280 MPa", [MaterialRecord(yield_strength="280 MPa")]),
    ]

    _merged_items, merged_records, stats = merge_records(chunks, items, max_chunk_distance=2)

    assert stats.merged_count == 0
    assert stats.unmatched_count == 2
    kinds = sorted(r.record_kind for r in merged_records)
    assert kinds == ["mechanics_only", "process_only"]
    assert all(r.merge_note for r in merged_records)
