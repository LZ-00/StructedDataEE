"""LoRA 适配器配置（参考 DSE LoRAModelSetup）。"""

from __future__ import annotations

from typing import Any, Callable, List, Optional

LogFn = Callable[[str, str], None]


def apply_lora(
    model: Any,
    *,
    r: int,
    alpha: int,
    dropout: float,
    target_modules: Optional[List[str]] = None,
    on_log: Optional[LogFn] = None,
) -> Any:
    from peft import LoraConfig, TaskType, get_peft_model

    modules = target_modules or [
        "q_proj",
        "k_proj",
        "v_proj",
        "o_proj",
        "gate_proj",
        "up_proj",
        "down_proj",
    ]
    lora_config = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        r=r,
        lora_alpha=alpha,
        lora_dropout=dropout,
        target_modules=modules,
        bias="none",
    )
    if on_log:
        on_log(f"  → LoRA r={r}, alpha={alpha}, dropout={dropout}", "INFO")
        on_log(f"  → target_modules: {', '.join(modules)}", "INFO")
    model = get_peft_model(model, lora_config)
    return model
