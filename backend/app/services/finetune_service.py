"""模型微调业务门面（LoRA）。"""

from __future__ import annotations

from typing import Any

from app.config import model_catalog as catalog
from app.services import model_config_service


def get_finetune_options() -> dict[str, Any]:
    from app.finetune.catalog import describe_finetune_dataset, finetune_output_base

    defaults = dict(catalog.FINETUNE_DEFAULTS)
    defaults["baseModel"] = model_config_service.get_default_model_id("finetune")

    return {
        "base_models": model_config_service.get_select_options(usage="finetune", types=["local"]),
        "learning_rates": catalog.FINETUNE_LEARNING_RATES,
        "defaults": defaults,
        "training_dataset": describe_finetune_dataset(),
        "finetune_output_dir": str(finetune_output_base()),
    }


def run_lora_finetune(config: dict[str, Any]) -> dict[str, Any]:
    """同步 LoRA 微调（无流式日志）。"""
    from app.finetune.pipeline import run_lora_finetune as _run

    from app.finetune.config import FineTuneParams

    return _run(FineTuneParams.from_request(config))


def publish_finetuned_model(
    model_name: str,
    *,
    checkpoint: str,
    base_model_registry_id: str,
    description: str = "",
) -> dict[str, Any]:
    """将 LoRA checkpoint 登记到模型注册表（评估库可选）。"""
    name = (model_name or "").strip()
    if not name:
        raise ValueError("模型名称不能为空")
    if not checkpoint:
        raise ValueError("checkpoint 路径不能为空")

    entry = model_config_service.get_model_internal(base_model_registry_id)
    if not entry or entry.get("type") != "local":
        raise ValueError("基座模型无效，无法登记微调结果")

    lc = entry.get("local_config") or {}
    ms_id = lc.get("model_id", "")
    base_dir = lc.get("base_dir", catalog.DEFAULT_LOCAL_BASE_DIR)

    from pathlib import Path

    from app.finetune.checkpoint_io import resolve_adapter_dir, verify_adapter_dir

    ckpt = Path(checkpoint)
    try:
        adapter_dir = resolve_adapter_dir(ckpt)
    except ValueError as exc:
        raise ValueError(str(exc)) from exc
    ok, verify_msg = verify_adapter_dir(adapter_dir)
    if not ok:
        raise ValueError(f"checkpoint 权重无效: {verify_msg}")

    desc = description or f"LoRA 微调产物，基座 {ms_id}，路径 {adapter_dir}"
    item = model_config_service.create_model(
        {
            "name": name,
            "type": "local",
            "enabled": True,
            "description": desc,
            "local_config": {
                "modelId": ms_id,
                "baseDir": base_dir,
                "localPath": str(adapter_dir),
            },
        }
    )
    return {
        "success": True,
        "registered_as": name,
        "model_id": item.get("id"),
        "checkpoint": str(adapter_dir),
        "message": f"模型「{name}」已保存并同步至评估库",
    }


def publish_model(model_name: str) -> dict[str, Any]:
    """兼容旧接口：仅名称时登记为展示用条目（无 checkpoint）。"""
    if not model_name or not str(model_name).strip():
        raise ValueError("模型名称不能为空")
    return {
        "success": True,
        "registered_as": model_name.strip(),
        "message": "已保存至评估库（演示）",
    }
