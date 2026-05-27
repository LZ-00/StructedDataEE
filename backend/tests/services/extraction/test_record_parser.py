import pytest

from app.schemas.extraction import MaterialRecord
from app.services.extraction.record_parser import (
    coerce_scalar_to_optional_str,
    normalize_record,
    parse_extraction_records,
)


def test_coerce_int_float_to_string():
    assert coerce_scalar_to_optional_str(2300) == "2300"
    assert coerce_scalar_to_optional_str(2.4) == "2.4"
    assert coerce_scalar_to_optional_str(2.0) == "2"


def test_coerce_string_and_empty():
    assert coerce_scalar_to_optional_str(" 2.8 kW ") == "2.8 kW"
    assert coerce_scalar_to_optional_str("") is None
    assert coerce_scalar_to_optional_str(None) is None


def test_material_record_from_numeric_dict():
    record = MaterialRecord.from_dict(
        {
            "welding_power": 2300,
            "welding_speed": 2.4,
            "shielding_gas": "Ar",
        }
    )
    assert record.welding_power == "2300"
    assert record.welding_speed == "2.4"
    assert record.shielding_gas == "Ar"


def test_parse_extraction_records_with_numeric_json():
    raw = """[
        {"welding_power": 2300, "welding_speed": 2.4, "shielding_gas": "Ar"}
    ]"""
    records = parse_extraction_records(raw)
    assert len(records) == 1
    assert records[0].welding_power == "2300"
    assert records[0].welding_speed == "2.4"


def test_normalize_record_list_join():
    data = normalize_record({"welding_power": [2300, "2.8 kW"]})
    assert data["welding_power"] == "2300, 2.8 kW"
