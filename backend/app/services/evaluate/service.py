"""思维链评估服务聚合层。"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from app.services.evaluate import runner, sample_builder, uploaded_parser


def build_uploaded_samples(raw: bytes, filename: str | None = None) -> list[sample_builder.EvaluationSample]:
    records = uploaded_parser.parse_uploaded_records(raw, filename)
    return sample_builder.build_samples(records)


def iter_sse_lines(
    model: str,
    raw: bytes,
    filename: str | None = None,
    *,
    samples: list[sample_builder.EvaluationSample] | None = None,
    cancel_event=None,
) -> Iterator[str]:
    sample_list = samples or build_uploaded_samples(raw, filename)
    return runner.iter_uploaded_sse_lines(model, sample_list, cancel_event=cancel_event)


def request_cancel_event():
    return runner.request_cancel_event()


def get_evaluation_options(models: list[dict[str, str]]) -> dict[str, Any]:
    return {
        "models": models,
        "step_descriptions": [
            "解析 AI Prediction 中所有非空字段-值对",
            "仅基于 Context 核验字段值与单位",
            "按字段、值、单位、关联关系判定正误",
            "统计正确预测数与非空预测总数",
        ],
        "example_cot_log": (
            "Step 1: Parse all non-null field-value pairs from the AI Prediction for the laser "
            "welding experimental record.\n"
            "Step 2: Check each prediction against the Context as the only evidence source, "
            "allowing only meaning-preserving unit or lexical variants.\n"
            "Step 3: Mark each prediction as 'Correct' only when its field, value, unit, and "
            "association with the welding record are explicitly supported by the Context; "
            "otherwise mark it as 'Incorrect'.\n"
            "Step 4: Reconcile the number of correct predictions with the total number of "
            "non-null predicted relations.\n"
            '{"correctly_predicted_relations": 1, "total_predicted_relations": 1}'
        ),
    }
