"""抽取流水线统一 LLM 调用入口。"""

from __future__ import annotations

from app.services import model_config_service, model_test_service

_EXTRACTION_TEMPERATURE = 0.1
_EXTRACTION_MAX_NEW_TOKENS = 2048


def invoke_registered_model(registry_id: str, prompt: str) -> str:
    entry = model_config_service.get_model_internal(registry_id)
    if not entry:
        raise ValueError(f"模型不存在: {registry_id}")
    if not entry.get("enabled", True):
        raise ValueError(f"模型未启用: {registry_id}")

    if entry.get("type") == "api":
        api = entry.get("api_config") or {}
        result = model_test_service.invoke_api_chat_completion(
            model_id=(api.get("model_id") or "").strip(),
            api_key=api.get("api_key", ""),
            base_url=api.get("base_url", ""),
            user_content=prompt,
            temperature=_EXTRACTION_TEMPERATURE,
            max_tokens=int(api.get("max_tokens") or 4096),
            timeout_sec=300,
        )
        if not result.get("success"):
            raise RuntimeError(result.get("message", "API 模型调用失败"))
        return (result.get("content") or "").strip()

    lc = entry.get("local_config") or {}
    session = model_test_service.open_local_inference_session(
        lc.get("model_id", ""),
        lc.get("base_dir", ""),
        lc.get("local_path", ""),
        max_new_tokens=_EXTRACTION_MAX_NEW_TOKENS,
        temperature=_EXTRACTION_TEMPERATURE,
    )
    try:
        return session.generate("", prompt)
    finally:
        session.close()


def resolve_model_id(model: str) -> str:
    registry_id = (model or "").strip()
    if not registry_id:
        return model_config_service.get_default_model_id("extraction")
    return registry_id
