"""演示模式 LoRA 微调（无 GPU / 无依赖时）。"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Callable

from app.finetune.config import FineTuneParams

EmitFn = Callable[[dict[str, Any]], None]
LogFn = Callable[[str, str], None]


def _log(emit: EmitFn | None, msg: str, level: str = "INFO") -> None:
    if emit:
        from datetime import datetime, timezone

        emit(
            {
                "type": "log",
                "level": level,
                "time": datetime.now(timezone.utc).strftime("%H:%M:%S"),
                "message": msg,
            }
        )


def _step(emit: EmitFn | None, index: int, status: str) -> None:
    if emit:
        emit({"type": "step", "index": index, "status": status})


def run_demo_finetune(
    params: FineTuneParams,
    *,
    emit: EmitFn | None,
    output_dir: str,
    data_path: Path | None = None,
    data_info: dict | None = None,
    sample_count: int = 10,
) -> dict[str, Any]:
    epochs = params.num_epochs
    steps_per_epoch = max(4, min(sample_count, 8))

    _step(emit, 0, "process")
    _log(emit, "[Step 1/5] 准备训练数据（演示模式）")
    info = data_info or {}
    if info.get("source") == "distillation_saved":
        _log(emit, f"  → 最新 finetune 数据: {info.get('filename')} ({sample_count} 条)")
    elif data_path:
        _log(emit, f"  → 数据文件: {data_path.name} ({sample_count} 条)")
    _log(emit, f"  → 样本数: {sample_count} | 格式: Instruction/Input/Output JSONL")
    if data_path:
        _log(emit, f"  → 路径: {data_path}")
    time.sleep(0.2)
    _step(emit, 0, "finish")

    _step(emit, 1, "process")
    _log(emit, f"[Step 2/5] 加载基座模型: {params.base_model_registry_id}")
    _log(emit, "  → [demo] 模拟加载 ModelScope 权重与 tokenizer")
    time.sleep(0.25)
    _step(emit, 1, "finish")

    _step(emit, 2, "process")
    _log(emit, "[Step 3/5] 配置 LoRA 适配器")
    _log(emit, f"  → r={params.lora_r}, alpha={params.lora_alpha}, dropout={params.lora_dropout}")
    _log(emit, "  → target_modules: q_proj, k_proj, v_proj, o_proj, …")
    time.sleep(0.2)
    _step(emit, 2, "finish")

    _step(emit, 3, "process")
    _log(emit, "[Step 4/5] LoRA 微调训练（演示）")
    loss = 0.35
    for ep in range(1, epochs + 1):
        _log(emit, f"  Epoch {ep}/{epochs}:", "INFO")
        for step in range(1, steps_per_epoch + 1):
            loss = max(0.08, loss * 0.92)
            _log(
                emit,
                f"    Step {step}/{steps_per_epoch}: loss={loss:.4f}, lr={params.learning_rate:.2e}",
                "INFO",
            )
            time.sleep(0.06)
        _log(emit, f"  → Epoch {ep} 完成, avg_loss={loss:.4f}", "SUCCESS")
    _step(emit, 3, "finish")

    _step(emit, 4, "process")
    _log(emit, "[Step 5/5] 保存 LoRA 权重")
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "adapter_config.json").write_text(
        json.dumps(
            {
                "peft_type": "LORA",
                "demo": True,
                "r": params.lora_r,
                "lora_alpha": params.lora_alpha,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    _log(emit, f"  → checkpoint: {output_dir}")
    _step(emit, 4, "finish")

    suggested = params.model_name or "Qwen2.5-7B-Instruct-CoT-LoRA"
    ds_name = (info.get("filename") if info else None) or (data_path.name if data_path else "dataset")
    return {
        "success": True,
        "mode": "demo",
        "logs": [],
        "checkpoint": output_dir,
        "suggested_model_name": suggested,
        "dataset_path": str(data_path) if data_path else "",
        "dataset_filename": ds_name,
        "dataset_sample_count": sample_count,
        "message": f"LoRA 微调完成（演示模式，数据: {ds_name}，{epochs} epochs）",
    }
