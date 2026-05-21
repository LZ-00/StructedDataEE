"""训练过程日志回调。"""

from __future__ import annotations

from typing import Callable, Optional

LogFn = Callable[[str, str], None]


def build_log_callback(on_log: Optional[LogFn]):
    """构建 HuggingFace TrainerCallback，将 loss 写入 on_log。"""
    from transformers import TrainerCallback

    class _FinetuneLogCallback(TrainerCallback):
        def on_log(self, args, state, control, logs=None, **kwargs):
            if not on_log or not logs:
                return
            parts = []
            if "loss" in logs:
                parts.append(f"loss={logs['loss']:.4f}")
            if "learning_rate" in logs:
                parts.append(f"lr={logs['learning_rate']:.2e}")
            if "epoch" in logs:
                parts.append(f"epoch={logs['epoch']:.2f}")
            if parts:
                on_log(f"    · {' | '.join(parts)}", "INFO")

        def on_epoch_end(self, args, state, control, **kwargs):
            if on_log:
                on_log(f"  → Epoch {int(state.epoch)} 完成", "SUCCESS")

    return _FinetuneLogCallback()
