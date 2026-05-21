"""从模型注册表加载基座模型。"""

from __future__ import annotations

from typing import Any, Tuple

from app.config import model_catalog as catalog
from app.services import model_config_service, model_test_service


def load_base_model_from_registry(registry_id: str) -> Tuple[Any, Any, dict[str, str]]:
    """
    加载本地基座模型与 tokenizer。

    Returns:
        (model, tokenizer, meta)  meta 含 model_id, path, base_dir
    """
    entry = model_config_service.get_model_internal(registry_id)
    if not entry:
        raise ValueError(f"基座模型不存在: {registry_id}")
    if entry.get("type") != "local":
        raise ValueError("LoRA 微调仅支持本地部署的基座模型")

    lc = entry.get("local_config") or {}
    ms_id = (lc.get("model_id") or "").strip()
    base_dir = (lc.get("base_dir") or catalog.DEFAULT_LOCAL_BASE_DIR).strip()
    custom_path = (lc.get("local_path") or "").strip()

    path = model_test_service.validate_local_model_downloaded(ms_id, base_dir, custom_path)

    import torch
    from modelscope import AutoModelForCausalLM, AutoTokenizer

    load_kwargs: dict[str, Any] = {"device_map": "auto"}
    if "llama" in ms_id.lower():
        load_kwargs["torch_dtype"] = torch.float16
    else:
        load_kwargs["torch_dtype"] = "auto"

    model = AutoModelForCausalLM.from_pretrained(path, **load_kwargs)
    tokenizer = AutoTokenizer.from_pretrained(path)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    return model, tokenizer, {"model_id": ms_id, "path": path, "base_dir": base_dir}
