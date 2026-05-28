"""真实 LoRA 微调流水线（参考 DSE run_training）。"""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any, Callable, Optional

from app.finetune import catalog as ft_catalog
from app.finetune.callbacks import build_log_callback
from app.finetune.checkpoint_io import save_peft_adapter
from app.finetune.config import FineTuneParams
from app.finetune.dataset import FineTuneJsonlDataset
from app.finetune.lora_setup import apply_lora
from app.finetune.model_loader import load_base_model_from_registry
from app.timezone_utils import slug_now_asia_shanghai, time_now_asia_shanghai

EmitFn = Callable[[dict[str, Any]], None]
LogFn = Callable[[str, str], None]


def _ts() -> str:
    return time_now_asia_shanghai()


def _log(emit: EmitFn | None, msg: str, level: str = "INFO") -> None:
    if emit:
        emit({"type": "log", "level": level, "time": _ts(), "message": msg})


def _step(emit: EmitFn | None, index: int, status: str) -> None:
    if emit:
        emit({"type": "step", "index": index, "status": status})


def can_run_real_finetune() -> tuple[bool, str]:
    flag = ft_catalog.FINETUNE_FORCE_DEMO
    if flag in ("1", "true", "yes"):
        return False, "FINETUNE_FORCE_DEMO=1"
    try:
        import torch  # noqa: F401

        _ = torch.cuda.is_available
        from peft import LoraConfig  # noqa: F401
        from transformers import Trainer  # noqa: F401
    except (ImportError, AttributeError) as exc:
        return False, f"缺少依赖: {exc}"
    if flag not in ("0", "false", "no"):
        import torch

        if not torch.cuda.is_available():
            return False, "未检测到 CUDA，已切换演示模式"
    return True, ""


def run_lora_finetune(
    params: FineTuneParams,
    *,
    emit: EmitFn | None = None,
) -> dict[str, Any]:
    run_id = slug_now_asia_shanghai() + "_" + uuid.uuid4().hex[:8]
    output_dir = ft_catalog.checkpoint_dir(run_id)
    output_dir.mkdir(parents=True, exist_ok=True)
    _log(emit, f"  → 权重根目录: {ft_catalog.finetune_output_base()}")

    real_ok, reason = can_run_real_finetune()
    if not real_ok:
        _log(emit, f"  → {reason}", "WARN")
        from app.finetune.demo_pipeline import run_demo_finetune

        data_info = ft_catalog.describe_finetune_dataset()
        data_path = ft_catalog.resolve_finetune_dataset_path(params.training_dataset_path)
        if not data_path.is_file():
            raise FileNotFoundError(
                "未找到微调数据：请先在 CoT 校对界面保存，生成 finetune_*.jsonl"
            )
        sample_count = data_info.get("sample_count") or 10
        return run_demo_finetune(
            params,
            emit=emit,
            output_dir=str(output_dir),
            data_path=data_path,
            data_info=data_info,
            sample_count=sample_count,
        )

    def on_log(msg: str, level: str = "INFO") -> None:
        _log(emit, msg, level)

    _step(emit, 0, "process")
    _log(emit, "[Step 1/5] 准备训练数据")
    data_info = ft_catalog.describe_finetune_dataset()
    data_path = ft_catalog.resolve_finetune_dataset_path(params.training_dataset_path)
    if not data_path.is_file():
        raise FileNotFoundError(
            "未找到微调数据：请先在 CoT 校对界面保存，生成 finetune_*.jsonl"
        )
    if data_info.get("source") == "distillation_saved":
        extra = ""
        if int(data_info.get("candidate_count") or 0) > 1:
            extra = f"（共 {data_info['candidate_count']} 个 finetune 文件，已取最新）"
        _log(
            emit,
            f"  → 最新 finetune 数据: {data_info.get('filename')} "
            f"({data_info.get('sample_count', 0)} 条){extra}",
        )
    else:
        _log(
            emit,
            f"  → 数据文件: {data_info.get('filename')} "
            f"({data_info.get('sample_count', 0)} 条，非蒸馏保存)",
            "WARN",
        )
    max_samples = params.max_samples or ft_catalog.FINETUNE_MAX_SAMPLES or None
    _log(emit, f"  → 路径: {data_path}")
    _step(emit, 0, "finish")

    _step(emit, 1, "process")
    _log(emit, "[Step 2/5] 加载基座模型")
    model, tokenizer, meta = load_base_model_from_registry(params.base_model_registry_id)
    _log(emit, f"  → ModelScope ID: {meta['model_id']}")
    _log(emit, f"  → 路径: {meta['path']}")
    _step(emit, 1, "finish")

    _step(emit, 2, "process")
    _log(emit, "[Step 3/5] 配置 LoRA")
    model = apply_lora(
        model,
        r=params.lora_r,
        alpha=params.lora_alpha,
        dropout=params.lora_dropout,
        on_log=on_log,
    )
    _step(emit, 2, "finish")

    _step(emit, 3, "process")
    _log(emit, "[Step 4/5] 开始 LoRA 微调")
    train_dataset = FineTuneJsonlDataset(
        data_path,
        tokenizer,
        max_length=params.max_length or ft_catalog.FINETUNE_MAX_LENGTH,
        max_samples=max_samples,
    )
    _log(emit, f"  → 训练样本: {len(train_dataset)}")

    import torch
    from transformers import TrainingArguments, Trainer

    use_bf16 = bool(torch.cuda.is_available() and torch.cuda.is_bf16_supported())
    training_args = TrainingArguments(
        output_dir=str(output_dir),
        num_train_epochs=params.num_epochs,
        per_device_train_batch_size=params.batch_size,
        learning_rate=params.learning_rate,
        logging_steps=1,
        save_strategy="no",
        remove_unused_columns=False,
        bf16=use_bf16,
        fp16=not use_bf16 and torch.cuda.is_available(),
        report_to="none",
        warmup_steps=min(10, max(1, len(train_dataset) // 2)),
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        processing_class=tokenizer,
        callbacks=[build_log_callback(on_log)],
    )
    trainer.train()
    _log(emit, "  → 训练循环结束", "SUCCESS")
    _step(emit, 3, "finish")

    _step(emit, 4, "process")
    _log(emit, "[Step 5/5] 保存 LoRA 权重")
    adapter_path = save_peft_adapter(
        trainer.model,
        tokenizer,
        output_dir,
        on_log=on_log,
    )
    _log(emit, f"  → checkpoint: {adapter_path}")
    _step(emit, 4, "finish")

    suggested = params.model_name or f"{meta['model_id'].split('/')[-1]}-CoT-LoRA"
    return {
        "success": True,
        "mode": "lora",
        "checkpoint": str(adapter_path),
        "suggested_model_name": suggested,
        "base_model_registry_id": params.base_model_registry_id,
        "dataset_path": str(data_path),
        "dataset_filename": data_info.get("filename", data_path.name),
        "dataset_sample_count": data_info.get("sample_count", len(train_dataset)),
        "message": (
            f"LoRA 微调完成（数据: {data_info.get('filename', data_path.name)}，"
            f"{len(train_dataset)} 条），权重已保存至 {adapter_path}"
        ),
    }
