"""微调数据集（参考 DSE FineTuneDataset）。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional


class FineTuneJsonlDataset:
    """JSONL: Instruction / Input / Output 字段。"""

    @staticmethod
    def build_chat_text(
        tokenizer: Any,
        instruction: str,
        input_text: str,
        output_text: str | None = None,
        *,
        add_generation_prompt: bool = False,
    ) -> str:
        user_content = f"{instruction}\n\n{input_text}" if instruction else input_text
        if output_text is not None:
            messages = [
                {"role": "user", "content": user_content},
                {"role": "assistant", "content": output_text},
            ]
        else:
            messages = [{"role": "user", "content": user_content}]
        return tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=add_generation_prompt,
        )

    def __init__(
        self,
        data_path: Path,
        tokenizer: Any,
        *,
        max_length: int = 2048,
        max_samples: Optional[int] = None,
    ):
        self.tokenizer = tokenizer
        self.max_length = max_length
        self.data: list[dict[str, str]] = []
        with open(data_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                self.data.append(json.loads(line))
                if max_samples and len(self.data) >= max_samples:
                    break

    def __len__(self) -> int:
        return len(self.data)

    def __getitem__(self, idx: int) -> dict[str, Any]:
        import torch

        item = self.data[idx]
        instruction = item.get("Instruction", "")
        input_text = item.get("Input", "")
        output_text = item.get("Output", "")

        full_text = self.build_chat_text(
            self.tokenizer, instruction, input_text, output_text, add_generation_prompt=False
        )
        prompt_text = self.build_chat_text(
            self.tokenizer, instruction, input_text, None, add_generation_prompt=True
        )

        encoded = self.tokenizer(
            full_text,
            truncation=True,
            max_length=self.max_length,
            padding="max_length",
            return_tensors="pt",
        )
        prompt_encoded = self.tokenizer(
            prompt_text,
            truncation=True,
            max_length=self.max_length,
            return_tensors="pt",
        )

        labels = encoded["input_ids"].clone()
        prompt_length = prompt_encoded["input_ids"].shape[1]
        actual_length = int((encoded["attention_mask"] == 1).sum().item())
        prompt_length = min(prompt_length, actual_length)
        labels[0, :prompt_length] = -100
        labels[0, actual_length:] = -100

        return {
            "input_ids": encoded["input_ids"].squeeze(0),
            "attention_mask": encoded["attention_mask"].squeeze(0),
            "labels": labels.squeeze(0),
        }
