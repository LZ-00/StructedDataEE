"""评估样本构建器：上传记录 -> CoT 评估输入。"""

from __future__ import annotations

import json
from dataclasses import dataclass

from app.data.prompt import build_evaluation_input, get_evaluation_instruction
from app.services.evaluate.uploaded_parser import UploadedEvaluationRecord


@dataclass
class EvaluationSample:
    index: int
    record_id: str
    chunk_id: str
    passage: str
    ai_prediction_text: str
    instruction: str
    input_text: str


def build_samples(records: list[UploadedEvaluationRecord]) -> list[EvaluationSample]:
    instruction = get_evaluation_instruction()
    samples: list[EvaluationSample] = []
    for record in records:
        ai_prediction_text = _serialize_prediction(record)
        samples.append(
            EvaluationSample(
                index=record.index,
                record_id=record.record_id,
                chunk_id=record.chunk_id,
                passage=record.chunk_text,
                ai_prediction_text=ai_prediction_text,
                instruction=instruction,
                input_text=build_evaluation_input(
                    passage=record.chunk_text,
                    ai_prediction=ai_prediction_text,
                ),
            )
        )
    return samples


def _serialize_prediction(record: UploadedEvaluationRecord) -> str:
    welding = json.dumps(record.welding_parameters, ensure_ascii=False)
    mechanical = json.dumps(record.mechanical_performance, ensure_ascii=False)
    return (
        f"Record ID: {record.record_id}\n"
        f"Chunk ID: {record.chunk_id}\n"
        f"Welding Parameters: {welding}\n"
        f"Mechanical Performance: {mechanical}"
    )
