"""
模型连通性与推理检测（参考 DSE script/model_test.ipynb、utils/model.py）。

本地模型：解析 DSE 路径（`.` → `___`）→ 加载权重 → 短文本 generate。
API 模型：OpenAI 兼容 chat/completions 试调用。
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable, Optional

from app.config import model_catalog as catalog


def local_path_candidates(model_id: str, base_dir: str, custom_path: str = "") -> list[str]:
    """按 DSE 约定生成候选本地路径（去重、保序）。"""
    seen: set[str] = set()
    out: list[str] = []
    for raw in (
        custom_path.strip() if custom_path else "",
        str(Path(base_dir) / model_id.replace(".", "___")),
        str(Path(base_dir) / model_id),
    ):
        if not raw or raw in seen:
            continue
        seen.add(raw)
        out.append(raw)
    return out


def find_local_model_path(model_id: str, base_dir: str, custom_path: str = "") -> Optional[str]:
    """返回首个存在且含 config.json 的权重目录。"""
    for path in local_path_candidates(model_id, base_dir, custom_path):
        cfg = Path(path) / "config.json"
        if cfg.is_file():
            return path
    return None


def validate_local_model_downloaded(
    model_id: str,
    base_dir: str,
    custom_path: str = "",
) -> str:
    """
    校验本地权重已下载（目录存在且含 config.json）。
    通过则返回实际路径，否则抛出 ValueError。
    """
    ms_id = (model_id or "").strip()
    if not ms_id:
        raise ValueError("ModelScope 模型 ID 不能为空")

    custom = (custom_path or "").strip()
    if custom and (Path(custom) / "adapter_config.json").is_file():
        return str(Path(custom).resolve())

    path = find_local_model_path(ms_id, base_dir, custom_path)
    if path:
        return path

    tried = local_path_candidates(ms_id, base_dir, custom_path)
    hint = "；".join(tried) if tried else base_dir
    raise ValueError(
        f"本地模型尚未下载或路径无效（需包含 config.json 或 LoRA adapter_config.json）。"
        f"请先在模型配置页点击「下载」，或执行 model_install。候选路径：{hint}"
    )


def validate_api_model_accessible(
    *,
    model_id: str,
    api_key: str,
    base_url: str = "",
    temperature: float = 0.7,
    max_tokens: Optional[int] = None,
) -> None:
    """
    校验 API 模型可调用（OpenAI 兼容 chat/completions 试请求）。
    失败则抛出 ValueError。
    """
    mid = (model_id or "").strip()
    if not mid:
        raise ValueError("API 模型标识（model_id）不能为空")

    result = test_api_model_inference(
        model_id=mid,
        api_key=api_key,
        base_url=base_url,
        temperature=temperature,
        max_tokens=max_tokens or catalog.MODEL_VALIDATE_API_MAX_TOKENS,
    )
    if not result.get("success"):
        raise ValueError(result.get("message", "API 模型不可用"))


def _build_chat_messages(model_id: str) -> list[dict[str, str]]:
    prompt = catalog.MODEL_TEST_USER_PROMPT
    if "qwen" in model_id.lower():
        return [
            {
                "role": "system",
                "content": "You are Qwen, created by Alibaba Cloud. You are a helpful assistant.",
            },
            {"role": "user", "content": prompt},
        ]
    return [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": prompt},
    ]


def test_local_model_inference(
    model_id: str,
    base_dir: str,
    custom_path: str = "",
) -> dict[str, Any]:
    """加载本地模型并执行短推理（与 model_test.ipynb 流程一致）。"""
    path = find_local_model_path(model_id, base_dir, custom_path)
    if not path:
        tried = local_path_candidates(model_id, base_dir, custom_path)
        return {
            "success": False,
            "message": "未找到有效权重目录（需包含 config.json）",
            "path": tried[0] if tried else "",
            "tried_paths": tried,
        }

    try:
        import sys

        import torch
        from modelscope import AutoModelForCausalLM, AutoTokenizer
    except ImportError as e:
        py = sys.executable
        return {
            "success": False,
            "message": (
                f"当前后端 Python 未安装 modelscope/torch（解释器: {py}）。"
                "请使用 conda 环境 lz-HV-FT 启动：npm run dev:backend（勿用 backend/.venv）。"
                "或在当前环境执行: pip install modelscope torch"
            ),
            "path": path,
            "python_executable": py,
            "error": str(e),
        }

    t0 = time.perf_counter()
    is_llama = "llama" in model_id.lower()

    load_kwargs: dict[str, Any] = {"device_map": "auto"}
    if is_llama:
        load_kwargs["torch_dtype"] = torch.float16
    else:
        load_kwargs["torch_dtype"] = "auto"

    try:
        model = AutoModelForCausalLM.from_pretrained(path, **load_kwargs)
        tokenizer = AutoTokenizer.from_pretrained(path)
    except Exception as e:
        return {
            "success": False,
            "message": f"模型加载失败: {e}",
            "path": path,
            "elapsed_seconds": round(time.perf_counter() - t0, 2),
        }

    messages = _build_chat_messages(model_id)
    try:
        text = tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
        )
        model_inputs = tokenizer([text], return_tensors="pt").to(model.device)
        generated_ids = model.generate(
            **model_inputs,
            max_new_tokens=catalog.MODEL_TEST_MAX_NEW_TOKENS,
        )
        generated_ids = [
            output_ids[len(input_ids) :]
            for input_ids, output_ids in zip(model_inputs.input_ids, generated_ids)
        ]
        sample = tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]
    except Exception as e:
        return {
            "success": False,
            "message": f"推理失败: {e}",
            "path": path,
            "elapsed_seconds": round(time.perf_counter() - t0, 2),
        }
    finally:
        del model

    elapsed = round(time.perf_counter() - t0, 2)
    preview = sample.strip()
    if len(preview) > 280:
        preview = preview[:280] + "…"

    return {
        "success": True,
        "message": f"本地推理检测通过（耗时 {elapsed}s）",
        "path": path,
        "model_id": model_id,
        "sample_response": preview,
        "elapsed_seconds": elapsed,
    }


def invoke_api_chat_completion(
    *,
    model_id: str,
    api_key: str,
    base_url: str = "",
    user_content: str,
    temperature: float = 0.7,
    max_tokens: Optional[int] = None,
    timeout_sec: int = 180,
) -> dict[str, Any]:
    """调用 OpenAI 兼容 chat/completions（单轮 user 消息，供 CoT 生成等场景）。"""
    key = (api_key or os.getenv("OPENAI_API_KEY") or "").strip()
    if not key:
        return {
            "success": False,
            "message": "未配置 API Key，请在模型配置中填写或设置环境变量 OPENAI_API_KEY",
        }

    root = (base_url or os.getenv("OPENAI_BASE_URL") or "https://api.openai.com/v1").rstrip("/")
    url = f"{root}/chat/completions"
    payload = {
        "model": model_id,
        "messages": [{"role": "user", "content": user_content}],
        "max_tokens": max_tokens or catalog.MODEL_TEST_API_MAX_TOKENS,
        "temperature": temperature,
    }
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {key}",
        },
        method="POST",
    )

    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")[:500]
        return {
            "success": False,
            "message": f"API 请求失败 HTTP {e.code}: {detail}",
            "elapsed_seconds": round(time.perf_counter() - t0, 2),
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"API 请求失败: {e}",
            "elapsed_seconds": round(time.perf_counter() - t0, 2),
        }

    elapsed = round(time.perf_counter() - t0, 2)
    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        return {
            "success": False,
            "message": f"API 响应格式异常: {str(data)[:300]}",
            "elapsed_seconds": elapsed,
        }

    return {
        "success": True,
        "message": f"API 调用成功（耗时 {elapsed}s）",
        "model_id": model_id,
        "base_url": root,
        "content": (content or "").strip(),
        "elapsed_seconds": elapsed,
    }


def test_api_model_inference(
    *,
    model_id: str,
    api_key: str,
    base_url: str = "",
    temperature: float = 0.7,
    max_tokens: Optional[int] = None,
) -> dict[str, Any]:
    """调用 OpenAI 兼容 API 完成一次短对话检测。"""
    result = invoke_api_chat_completion(
        model_id=model_id,
        api_key=api_key,
        base_url=base_url,
        user_content=catalog.MODEL_TEST_USER_PROMPT,
        temperature=temperature,
        max_tokens=max_tokens or catalog.MODEL_TEST_API_MAX_TOKENS,
        timeout_sec=120,
    )
    if not result.get("success"):
        return result

    preview = (result.get("content") or "").strip()
    if len(preview) > 280:
        preview = preview[:280] + "…"

    return {
        "success": True,
        "message": f"API 推理检测通过（耗时 {result.get('elapsed_seconds')}s）",
        "model_id": model_id,
        "base_url": result.get("base_url"),
        "sample_response": preview,
        "elapsed_seconds": result.get("elapsed_seconds"),
    }


def invoke_api_chat_completion_stream(
    *,
    model_id: str,
    api_key: str,
    base_url: str = "",
    user_content: str,
    temperature: float = 0.7,
    max_tokens: Optional[int] = None,
    on_chunk: Callable[[str], None],
    cancel_event: Any = None,
    timeout_sec: int = 300,
) -> str:
    """OpenAI 兼容流式 chat/completions，逐段回调 on_chunk。"""
    key = (api_key or os.getenv("OPENAI_API_KEY") or "").strip()
    if not key:
        raise RuntimeError("未配置 API Key")

    root = (base_url or os.getenv("OPENAI_BASE_URL") or "https://api.openai.com/v1").rstrip("/")
    url = f"{root}/chat/completions"
    payload = {
        "model": model_id,
        "messages": [{"role": "user", "content": user_content}],
        "max_tokens": max_tokens or catalog.MODEL_TEST_API_MAX_TOKENS,
        "temperature": temperature,
        "stream": True,
    }
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {key}",
        },
        method="POST",
    )

    parts: list[str] = []
    with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
        for raw_line in resp:
            if cancel_event is not None and cancel_event.is_set():
                break
            line = raw_line.decode("utf-8", errors="replace").strip()
            if not line or not line.startswith("data:"):
                continue
            data_str = line[5:].strip()
            if data_str == "[DONE]":
                break
            try:
                data = json.loads(data_str)
            except json.JSONDecodeError:
                continue
            choices = data.get("choices") or []
            if not choices:
                continue
            delta = choices[0].get("delta") or {}
            content = delta.get("content")
            if content:
                parts.append(content)
                on_chunk(content)
    return "".join(parts).strip()


def test_registered_model(item: dict[str, Any]) -> dict[str, Any]:
    """根据注册表条目执行检测。"""
    if item.get("type") == "local":
        lc = item.get("local_config") or {}
        return test_local_model_inference(
            lc.get("model_id", ""),
            lc.get("base_dir", catalog.DEFAULT_LOCAL_BASE_DIR),
            lc.get("local_path", ""),
        )

    api = item.get("api_config") or {}
    return test_api_model_inference(
        model_id=api.get("model_id", ""),
        api_key=api.get("api_key", ""),
        base_url=api.get("base_url", ""),
        temperature=float(api.get("temperature", 0.7)),
        max_tokens=int(api.get("max_tokens", catalog.MODEL_TEST_API_MAX_TOKENS)),
    )


def resolve_local_weights(
    model_id: str,
    base_dir: str,
    custom_path: str = "",
) -> tuple[str, Optional[str]]:
    """
    解析本地权重路径。

    Returns:
        (base_model_path, adapter_path) — adapter_path 非空时表示 LoRA 目录
    """
    ms_id = (model_id or "").strip()
    custom = (custom_path or "").strip()
    if custom and (Path(custom) / "adapter_config.json").is_file():
        base = find_local_model_path(ms_id, base_dir, "")
        if not base:
            tried = local_path_candidates(ms_id, base_dir, "")
            hint = "；".join(tried) if tried else base_dir
            raise ValueError(
                f"已指定 LoRA 目录但未找到基座权重（需 config.json）。候选：{hint}"
            )
        return base, str(Path(custom).resolve())

    path = find_local_model_path(ms_id, base_dir, custom_path)
    if path:
        return path, None

    tried = local_path_candidates(ms_id, base_dir, custom_path)
    hint = "；".join(tried) if tried else base_dir
    raise ValueError(
        f"本地模型尚未下载或路径无效（需包含 config.json 或 LoRA adapter_config.json）。候选：{hint}"
    )


def build_eval_chat_prompt(tokenizer: Any, instruction: str, input_text: str) -> str:
    """构建评估推理 prompt（对齐 DSE FineTuneDataset.build_chat_template）。"""
    user_content = f"{instruction.rstrip()}\n\n{input_text}" if instruction else input_text
    messages = [{"role": "user", "content": user_content}]
    return tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
    )


class LocalInferenceSession:
    """本地模型推理会话：单次评估任务内复用已加载权重。"""

    def __init__(
        self,
        model_id: str,
        base_dir: str,
        custom_path: str = "",
        *,
        max_new_tokens: int = 1024,
        max_length: int = 3000,
        temperature: float = 0.0,
    ) -> None:
        self._model_id = model_id
        self._max_new_tokens = max_new_tokens
        self._max_length = max_length
        self._temperature = temperature
        self._model: Any = None
        self._tokenizer: Any = None
        self._base_path, self._adapter_path = resolve_local_weights(
            model_id, base_dir, custom_path
        )
        self._load()

    def _load(self) -> None:
        try:
            import torch
            from modelscope import AutoModelForCausalLM, AutoTokenizer
        except ImportError as e:
            raise RuntimeError(
                "当前环境未安装 modelscope/torch，请使用 conda 环境 lz-HV-FT 启动后端"
            ) from e

        is_llama = "llama" in self._model_id.lower()
        load_kwargs: dict[str, Any] = {"device_map": "auto"}
        if is_llama:
            load_kwargs["torch_dtype"] = torch.float16
        else:
            load_kwargs["torch_dtype"] = "auto"

        self._model = AutoModelForCausalLM.from_pretrained(self._base_path, **load_kwargs)
        self._tokenizer = AutoTokenizer.from_pretrained(self._base_path)
        if self._tokenizer.pad_token is None:
            self._tokenizer.pad_token = self._tokenizer.eos_token

        if self._adapter_path:
            from peft import PeftModel

            self._model = PeftModel.from_pretrained(self._model, self._adapter_path)
        self._model.eval()

    def _prepare_generation(self, instruction: str, input_text: str) -> tuple[Any, dict[str, Any], int]:
        import torch

        if self._model is None or self._tokenizer is None:
            raise RuntimeError("本地模型未加载")

        prompt_text = build_eval_chat_prompt(self._tokenizer, instruction, input_text)
        inputs = self._tokenizer(
            prompt_text,
            return_tensors="pt",
            truncation=True,
            max_length=self._max_length,
        )
        device = next(self._model.parameters()).device
        inputs = {k: v.to(device) for k, v in inputs.items()}
        input_len = int(inputs["input_ids"].shape[1])

        gen_kwargs: dict[str, Any] = {
            "max_new_tokens": self._max_new_tokens,
            "pad_token_id": self._tokenizer.pad_token_id,
            "eos_token_id": self._tokenizer.eos_token_id,
            "do_sample": self._temperature > 0.0,
        }
        if self._temperature > 0.0:
            gen_kwargs["temperature"] = self._temperature
        return inputs, gen_kwargs, input_len

    def generate(self, instruction: str, input_text: str) -> str:
        import torch

        inputs, gen_kwargs, input_len = self._prepare_generation(instruction, input_text)
        with torch.no_grad():
            outputs = self._model.generate(**inputs, **gen_kwargs)
        new_tokens = outputs[0][input_len:]
        return self._tokenizer.decode(new_tokens, skip_special_tokens=True).strip()

    def generate_stream(
        self,
        instruction: str,
        input_text: str,
        *,
        on_chunk: Callable[[str], None],
        cancel_event: Any = None,
    ) -> str:
        """流式生成，每产出 token 片段调用 on_chunk。"""
        import threading

        import torch
        from transformers import TextIteratorStreamer

        inputs, gen_kwargs, _input_len = self._prepare_generation(instruction, input_text)
        streamer = TextIteratorStreamer(
            self._tokenizer,
            skip_prompt=True,
            skip_special_tokens=True,
        )
        gen_kwargs = {**gen_kwargs, "streamer": streamer}

        cancelled = threading.Event()

        def _generate() -> None:
            with torch.no_grad():
                self._model.generate(**inputs, **gen_kwargs)

        thread = threading.Thread(target=_generate, daemon=True)
        thread.start()

        parts: list[str] = []
        for text in streamer:
            if cancel_event is not None and cancel_event.is_set():
                cancelled.set()
                break
            if text:
                parts.append(text)
                on_chunk(text)
        thread.join(timeout=5)
        if cancel_event is not None and cancel_event.is_set():
            raise RuntimeError("用户已中止评估")
        return "".join(parts).strip()

    def close(self) -> None:
        import gc

        try:
            import torch
        except ImportError:
            torch = None  # type: ignore

        if self._model is not None:
            del self._model
            self._model = None
        if self._tokenizer is not None:
            del self._tokenizer
            self._tokenizer = None
        gc.collect()
        if torch is not None and torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.synchronize()


def open_local_inference_session(
    model_id: str,
    base_dir: str,
    custom_path: str = "",
    *,
    max_new_tokens: int = 1024,
    max_length: int = 3000,
    temperature: float = 0.0,
) -> LocalInferenceSession:
    """打开可复用的本地推理会话（评估基准批量推理）。"""
    return LocalInferenceSession(
        model_id,
        base_dir,
        custom_path,
        max_new_tokens=max_new_tokens,
        max_length=max_length,
        temperature=temperature,
    )
