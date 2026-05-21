"""LoRA checkpoint 保存、解析与校验。"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Callable, Optional

from app.finetune.catalog import finetune_output_base

LogFn = Optional[Callable[[str, str], None]]


def _log(on_log: LogFn, msg: str, level: str = "INFO") -> None:
    if on_log:
        on_log(msg, level)


def _has_adapter_weights(directory: Path) -> bool:
    for name in ("adapter_model.safetensors", "adapter_model.bin"):
        p = directory / name
        if p.is_file() and p.stat().st_size > 1024:
            return True
    return False


def verify_adapter_dir(directory: Path) -> tuple[bool, str]:
    """校验 LoRA 目录是否包含配置与权重文件。"""
    d = Path(directory)
    if not d.is_dir():
        return False, f"目录不存在: {d}"
    if not (d / "adapter_config.json").is_file():
        return False, "缺少 adapter_config.json"
    if not _has_adapter_weights(d):
        return False, "缺少有效的 adapter 权重文件"
    for weight in ("adapter_model.safetensors", "adapter_model.bin"):
        p = d / weight
        if not p.is_file():
            continue
        try:
            if weight.endswith(".safetensors"):
                from safetensors import safe_open

                with safe_open(str(p), framework="pt") as f:
                    _ = list(f.keys())
            else:
                import torch

                torch.load(p, map_location="cpu", weights_only=True)
        except Exception as exc:
            return False, f"{weight} 损坏或无法读取: {exc}"
    return True, ""


def resolve_adapter_dir(run_dir: Path) -> Path:
    """解析 LoRA 权重目录（须为含 adapter 文件的 run 目录）。"""
    root = Path(run_dir).resolve()
    if not root.is_dir():
        raise ValueError(f"checkpoint 目录不存在: {root}")
    if (root / "adapter_config.json").is_file() and _has_adapter_weights(root):
        return root
    raise ValueError(
        f"未找到有效的 LoRA 权重（需 adapter_config.json + adapter_model.*）: {root}"
    )


def _disk_usage_path(path: Path) -> Path:
    p = path
    while not p.exists():
        parent = p.parent
        if parent == p:
            break
        p = parent
    return p


def _save_state_dict_fallback(model, adapter_dir: Path, on_log: LogFn) -> None:
    from peft import get_peft_model_state_dict
    from safetensors.torch import save_file

    state = get_peft_model_state_dict(model)
    cpu_state = {k: v.detach().cpu().contiguous() for k, v in state.items()}
    save_file(cpu_state, adapter_dir / "adapter_model.safetensors")
    if hasattr(model, "peft_config"):
        for cfg in model.peft_config.values():
            cfg.save_pretrained(adapter_dir)
    _log(on_log, "  → 已使用 state_dict 回退保存", "WARN")


def save_peft_adapter(
    model,
    tokenizer,
    output_dir: Path,
    *,
    on_log: LogFn = None,
) -> Path:
    """保存 PEFT LoRA 到 output_dir 根目录（与 DSE trainer.save_model 布局一致）。"""
    from peft import PeftModel

    import torch

    if not isinstance(model, PeftModel):
        raise TypeError("当前模型未应用 LoRA，无法保存 adapter")

    root = Path(output_dir)
    usage = shutil.disk_usage(_disk_usage_path(finetune_output_base()))
    min_free = 512 * 1024 * 1024
    if usage.free < min_free:
        free_mb = usage.free // (1024 * 1024)
        raise RuntimeError(
            f"磁盘空间不足（剩余约 {free_mb} MB），无法安全保存 LoRA。"
            f"请清理 {finetune_output_base()} 或系统盘后再试。"
        )

    root.mkdir(parents=True, exist_ok=True)

    if torch.cuda.is_available():
        torch.cuda.synchronize()

    _log(on_log, f"  → 写入 LoRA: {root}")
    try:
        model.save_pretrained(str(root), safe_serialization=True)
    except RuntimeError as exc:
        err = str(exc)
        if "enforce fail" in err or "unexpected pos" in err:
            _log(on_log, f"  → save_pretrained 异常，回退: {err[:120]}", "WARN")
            _save_state_dict_fallback(model, root, on_log)
        else:
            raise

    tokenizer.save_pretrained(root)

    ok, msg = verify_adapter_dir(root)
    if not ok:
        raise RuntimeError(f"LoRA 保存后校验失败: {msg}")

    _log(on_log, "  → LoRA 权重校验通过", "SUCCESS")
    return root.resolve()
