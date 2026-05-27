import json

from app.services.evaluate.sample_builder import build_samples
from app.services.evaluate.uploaded_parser import UploadedEvaluationRecord


def test_build_samples_contains_context_and_prediction():
    records = [
        UploadedEvaluationRecord(
            index=1,
            record_id="R001",
            chunk_id="c-001",
            chunk_text="Laser welding paragraph.",
            welding_parameters={
                "welding_power": "2800 W",
                "welding_speed": "1.2 m/min",
                "defocusing_distance": None,
                "shielding_gas": "Argon",
                "shielding_gas_flow_rate": "20 L/min",
            },
            mechanical_performance={
                "tensile_strength": "286 MPa",
                "yield_strength": "175 MPa",
                "elongation_rate": "7.8%",
            },
        )
    ]

    samples = build_samples(records)

    assert len(samples) == 1
    sample = samples[0]
    assert "[Context]" in sample.input_text
    assert "Laser welding paragraph." in sample.input_text
    assert "Welding Parameters:" in sample.ai_prediction_text
    assert "Mechanical Performance:" in sample.ai_prediction_text
    parsed = json.loads(sample.ai_prediction_text.split("Welding Parameters: ", 1)[1].split("\n", 1)[0])
    assert parsed["welding_power"] == "2800 W"
