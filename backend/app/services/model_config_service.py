"""系统模型注册表：支持 API 调用与本地部署两种接入方式（参考 DSE ModelLoader / ClosedModelLoader）。"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal, Optional

from app.config import model_catalog as catalog
from app.services import model_test_service

_REGISTRY_PATH = Path(__file__).resolve().parent.parent / "data" / "models_registry.json"
_DEFAULT_BASE_DIR = catalog.DEFAULT_LOCAL_BASE_DIR

ModelType = Literal["api", "local"]
ModelUsage = catalog.ModelUsage

_registry: list[dict[str, Any]] = []


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _mask_secret(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 8:
        return "*" * len(value)
    return value[:4] + "****" + value[-4:]


def resolve_local_path(model_id: str, base_dir: str, custom_path: str = "") -> str:
    """本地权重路径：优先已存在目录，否则按 DSE ModelLoader（`.` → `___`）解析。"""
    found = model_test_service.find_local_model_path(model_id, base_dir, custom_path)
    if found:
        return found
    candidates = model_test_service.local_path_candidates(model_id, base_dir, custom_path)
    return candidates[0] if candidates else str(Path(base_dir) / model_id.replace(".", "___"))


def _seed_defaults() -> list[dict[str, Any]]:
    now = _now_iso()
    seeded: list[dict[str, Any]] = []
    for item in catalog.REGISTRY_SEED_MODELS:
        entry = dict(item)
        entry.setdefault("created_at", now)
        entry.setdefault("updated_at", now)
        seeded.append(entry)
    return seeded


def _load_registry() -> None:
    global _registry
    if _REGISTRY_PATH.is_file():
        try:
            with open(_REGISTRY_PATH, encoding="utf-8") as f:
                data = json.load(f)
            _registry = data if isinstance(data, list) else []
            return
        except (json.JSONDecodeError, OSError):
            pass
    _registry = _seed_defaults()
    _save_registry()


def _save_registry() -> None:
    _REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(_REGISTRY_PATH, "w", encoding="utf-8") as f:
        json.dump(_registry, f, ensure_ascii=False, indent=2)


def _public_item(item: dict[str, Any]) -> dict[str, Any]:
    out = dict(item)
    api = out.get("api_config")
    if isinstance(api, dict) and api.get("api_key"):
        api = dict(api)
        api["api_key_masked"] = _mask_secret(api["api_key"])
        api["api_key"] = ""
        out["api_config"] = api
    if out.get("type") == "local":
        lc = out.get("local_config") or {}
        out["resolved_path"] = resolve_local_path(
            lc.get("model_id", ""),
            lc.get("base_dir", _DEFAULT_BASE_DIR),
            lc.get("local_path", ""),
        )
    return out


def _model_list_sort_key(item: dict[str, Any]) -> tuple[int, str]:
    """已启用优先，同组内按名称排序。"""
    enabled_first = 0 if item.get("enabled", True) else 1
    return (enabled_first, (item.get("name") or "").casefold())


def list_models(*, include_disabled: bool = False) -> list[dict[str, Any]]:
    _load_registry()
    items = _registry if include_disabled else [m for m in _registry if m.get("enabled", True)]
    items = sorted(items, key=_model_list_sort_key)
    return [_public_item(m) for m in items]


def get_model(model_id: str) -> Optional[dict[str, Any]]:
    _load_registry()
    for m in _registry:
        if m.get("id") == model_id:
            return _public_item(m)
    return None


def get_model_internal(model_id: str) -> Optional[dict[str, Any]]:
    _load_registry()
    for m in _registry:
        if m.get("id") == model_id:
            return m
    return None


def _normalize_model_name(name: str) -> str:
    return (name or "").strip().casefold()


def _model_name_exists(name: str, *, exclude_id: Optional[str] = None) -> bool:
    """注册表中是否已有同名模型（名称忽略首尾空格与大小写）。"""
    key = _normalize_model_name(name)
    if not key:
        return False
    for m in _registry:
        if exclude_id and m.get("id") == exclude_id:
            continue
        if _normalize_model_name(str(m.get("name", ""))) == key:
            return True
    return False


def _assert_unique_model_name(name: str, *, exclude_id: Optional[str] = None) -> None:
    display = (name or "").strip()
    if _model_name_exists(display, exclude_id=exclude_id):
        raise ValueError(f"模型名称「{display}」已存在，请使用其他名称")


def models_as_select_options(
    *,
    types: Optional[list[ModelType]] = None,
) -> list[dict[str, str]]:
    """从注册表生成 {label, value} 下拉项。"""
    opts: list[dict[str, str]] = []
    for m in list_models():
        if types and m.get("type") not in types:
            continue
        tag = "API" if m.get("type") == "api" else "本地"
        opts.append({"label": f"{m['name']} [{tag}]", "value": m["id"]})
    return opts


def get_select_options(
    *,
    usage: Optional[ModelUsage] = None,
    types: Optional[list[ModelType]] = None,
) -> list[dict[str, str]]:
    """
    获取业务模块可用模型列表：优先注册表，否则回退至 model_catalog 中的静态配置。
    """
    registered = models_as_select_options(types=types)
    if registered:
        return registered
    if usage:
        return catalog.fallback_select_options(usage, types=types)
    return []


def get_default_model_id(usage: ModelUsage) -> str:
    """某业务场景的默认模型 id（注册表首项优先，否则 catalog 默认值）。"""
    type_filter: Optional[list[ModelType]] = None
    if usage == "finetune":
        type_filter = ["local"]
    elif usage == "distillation_teacher":
        type_filter = ["api"]

    options = get_select_options(usage=usage, types=type_filter)
    if options:
        preferred = catalog.resolve_default_model_id(usage)
        if any(o["value"] == preferred for o in options):
            return preferred
        return options[0]["value"]
    return catalog.resolve_default_model_id(usage)


def _validate_model_item(item: dict[str, Any]) -> None:
    """写入注册表前校验：本地权重已下载，或 API 可连通。"""
    model_type = item.get("type")
    if model_type == "local":
        lc = item.get("local_config") or {}
        model_test_service.validate_local_model_downloaded(
            lc.get("model_id", ""),
            lc.get("base_dir", _DEFAULT_BASE_DIR),
            lc.get("local_path", ""),
        )
        return

    if model_type == "api":
        api = item.get("api_config") or {}
        model_test_service.validate_api_model_accessible(
            model_id=api.get("model_id", ""),
            api_key=api.get("api_key", ""),
            base_url=api.get("base_url", ""),
            temperature=float(api.get("temperature", 0.7)),
            max_tokens=int(api.get("max_tokens") or catalog.MODEL_TEST_API_MAX_TOKENS),
        )
        return

    raise ValueError("模型类型必须为 api 或 local")


def get_form_options() -> dict[str, Any]:
    return {
        "default_base_dir": _DEFAULT_BASE_DIR,
        "model_types": [
            {"label": "API 远程调用", "value": "api"},
            {"label": "本地模型部署", "value": "local"},
        ],
        "example_model_ids": catalog.FORM_EXAMPLE_MODELSCOPE_IDS,
        "example_api_models": catalog.FORM_EXAMPLE_API_MODEL_IDS,
    }


def create_model(payload: dict[str, Any]) -> dict[str, Any]:
    _load_registry()
    model_type = payload.get("type")
    if model_type not in ("api", "local"):
        raise ValueError("模型类型必须为 api 或 local")

    name = (payload.get("name") or "").strip()
    if not name:
        raise ValueError("模型显示名称不能为空")
    _assert_unique_model_name(name)

    item: dict[str, Any] = {
        "id": str(uuid.uuid4()),
        "name": name,
        "type": model_type,
        "enabled": bool(payload.get("enabled", True)),
        "description": (payload.get("description") or "").strip(),
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
    }

    if model_type == "api":
        api = payload.get("api_config") or {}
        model_id = (api.get("model_id") or api.get("modelId") or "").strip()
        if not model_id:
            raise ValueError("API 模型标识（model_id）不能为空")
        item["api_config"] = {
            "base_url": (api.get("base_url") or api.get("baseUrl") or "").strip(),
            "api_key": (api.get("api_key") or api.get("apiKey") or "").strip(),
            "model_id": model_id,
            "temperature": float(api.get("temperature", 0.7)),
            "max_tokens": int(api.get("max_tokens") or api.get("maxTokens") or 4096),
        }
        item["local_config"] = None
    else:
        local = payload.get("local_config") or {}
        ms_id = (local.get("model_id") or local.get("modelId") or "").strip()
        if not ms_id:
            raise ValueError("ModelScope 模型 ID 不能为空")
        base_dir = (local.get("base_dir") or local.get("baseDir") or _DEFAULT_BASE_DIR).strip()
        item["local_config"] = {
            "model_id": ms_id,
            "base_dir": base_dir,
            "local_path": (local.get("local_path") or local.get("localPath") or "").strip(),
        }
        item["api_config"] = None

    # API 添加时校验连通性；本地模型允许先注册，再通过列表「下载」拉取权重
    if model_type == "api":
        _validate_model_item(item)
    _registry.append(item)
    _save_registry()
    return _public_item(item)


def update_model(model_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    _load_registry()
    idx = next((i for i, m in enumerate(_registry) if m.get("id") == model_id), None)
    if idx is None:
        raise ValueError("模型不存在")

    item = _registry[idx]
    if "name" in payload and (payload.get("name") or "").strip():
        new_name = payload["name"].strip()
        _assert_unique_model_name(new_name, exclude_id=model_id)
        item["name"] = new_name
    if "description" in payload:
        item["description"] = (payload.get("description") or "").strip()
    if "enabled" in payload:
        item["enabled"] = bool(payload["enabled"])

    if item["type"] == "api" and payload.get("api_config"):
        api = payload["api_config"]
        cfg = dict(item.get("api_config") or {})
        if "base_url" in api or "baseUrl" in api:
            cfg["base_url"] = (api.get("base_url") or api.get("baseUrl") or "").strip()
        if "model_id" in api or "modelId" in api:
            cfg["model_id"] = (api.get("model_id") or api.get("modelId") or "").strip()
        key_val = api.get("api_key") or api.get("apiKey")
        if key_val and str(key_val).strip():
            cfg["api_key"] = str(key_val).strip()
        if "temperature" in api:
            cfg["temperature"] = float(api["temperature"])
        max_tok = api.get("max_tokens") if "max_tokens" in api else api.get("maxTokens")
        if max_tok is not None:
            cfg["max_tokens"] = int(max_tok)
        item["api_config"] = cfg
    elif item["type"] == "local" and payload.get("local_config"):
        local = payload["local_config"]
        cfg = dict(item.get("local_config") or {})
        model_id_val = local.get("model_id") if "model_id" in local else local.get("modelId")
        if model_id_val is not None:
            mid = str(model_id_val).strip()
            if mid:
                cfg["model_id"] = mid
            elif not cfg.get("model_id"):
                raise ValueError("ModelScope 模型 ID 不能为空")
        if "base_dir" in local or "baseDir" in local:
            cfg["base_dir"] = (local.get("base_dir") or local.get("baseDir") or _DEFAULT_BASE_DIR).strip()
        if "local_path" in local or "localPath" in local:
            cfg["local_path"] = (local.get("local_path") or local.get("localPath") or "").strip()
        item["local_config"] = cfg

    if payload.get("api_config") or payload.get("local_config"):
        _validate_model_item(item)

    item["updated_at"] = _now_iso()
    _registry[idx] = item
    _save_registry()
    return _public_item(item)


def delete_model(model_id: str) -> None:
    _load_registry()
    global _registry
    before = len(_registry)
    _registry = [m for m in _registry if m.get("id") != model_id]
    if len(_registry) == before:
        raise ValueError("模型不存在")
    _save_registry()


def test_model_connection(model_id: str) -> dict[str, Any]:
    """模型检测：本地加载并短文本推理，或 API 试调用（参考 DSE model_test.ipynb）。"""
    item = get_model_internal(model_id)
    if not item:
        raise ValueError("模型不存在")
    return model_test_service.test_registered_model(item)


def download_local_model(model_id: str, base_dir: str) -> dict[str, Any]:
    """触发 ModelScope 下载（参考 DSE script/model_install.py）。"""
    ms_id = (model_id or "").strip()
    if not ms_id:
        raise ValueError("ModelScope 模型 ID 不能为空")

    target = resolve_local_path(ms_id, base_dir or _DEFAULT_BASE_DIR, "")
    try:
        from modelscope.hub.snapshot_download import snapshot_download
    except ImportError as e:
        raise RuntimeError("未安装 modelscope，请执行: pip install modelscope") from e

    downloaded_path = snapshot_download(model_id=ms_id, cache_dir=base_dir or _DEFAULT_BASE_DIR)
    return {
        "success": True,
        "message": f"模型已下载至 {downloaded_path}",
        "path": downloaded_path,
        "expected_path": target,
    }


_load_registry()
