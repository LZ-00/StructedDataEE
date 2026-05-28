"""微调超参配置（对应 DSE FineTuneConfig）。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class FineTuneParams:
    base_model_registry_id: str
    training_dataset_path: str = ""
    lora_r: int = 64
    lora_alpha: int = 128
    lora_dropout: float = 0.05
    num_epochs: int = 3
    batch_size: int = 1
    learning_rate: float = 2e-5
    model_name: str = ""
    max_length: int = 2048
    max_samples: int = 0

    @classmethod
    def from_request(cls, body: dict[str, Any]) -> FineTuneParams:
        lr_raw = body.get("learningRate") or body.get("learning_rate") or "2e-5"
        try:
            lr = float(lr_raw)
        except (TypeError, ValueError):
            lr = 2e-5
        return cls(
            base_model_registry_id=str(
                body.get("baseModel") or body.get("base_model") or ""
            ).strip(),
            training_dataset_path=str(
                body.get("trainingDatasetPath") or body.get("training_dataset_path") or ""
            ).strip(),
            lora_r=int(body.get("loraRank") or body.get("lora_r") or 64),
            lora_alpha=int(body.get("loraAlpha") or body.get("lora_alpha") or 128),
            lora_dropout=float(body.get("loraDropout") or body.get("lora_dropout") or 0.05),
            num_epochs=int(body.get("epoch") or body.get("num_epochs") or 3),
            batch_size=int(body.get("batchSize") or body.get("batch_size") or 1),
            learning_rate=lr,
            model_name=str(body.get("modelName") or body.get("model_name") or "").strip(),
        )
