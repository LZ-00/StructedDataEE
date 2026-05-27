import json

import pytest

from app.services.evaluate.uploaded_parser import parse_uploaded_records


def test_parse_uploaded_records_success():
    payload = {
        "experimental_records": [
            {
                "record_id": "R001",
                "welding_parameters": {"welding_power": "2800 W"},
                "mechanical_performance": {"tensile_strength": "286 MPa"},
                "source": {"chunk_id": "c-001", "chunk": "A sample paragraph."},
            }
        ]
    }
    raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")

    records = parse_uploaded_records(raw, "sample.json")

    assert len(records) == 1
    assert records[0].record_id == "R001"
    assert records[0].chunk_id == "c-001"
    assert records[0].chunk_text == "A sample paragraph."
    assert records[0].welding_parameters["welding_power"] == "2800 W"


def test_parse_uploaded_records_require_chunk():
    payload = {
        "experimental_records": [
            {
                "record_id": "R001",
                "source": {"chunk_id": "c-001", "chunk": ""},
            }
        ]
    }
    raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")

    with pytest.raises(ValueError, match="source.chunk"):
        parse_uploaded_records(raw, "bad.json")
