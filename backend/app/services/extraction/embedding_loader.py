"""BAAI/bge-m3 本地加载与向量编码（权重目录：/data/lz/modelscope/embedding）。"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from threading import Lock
from typing import Optional

import numpy as np

from app.config import embedding_catalog as emb_cfg

logger = logging.getLogger(__name__)

_model_lock = Lock()
_sentence_model: Optional[object] = None
_tokenizer: Optional[object] = None

_WEIGHT_FILENAMES = ("pytorch_model.bin", "model.safetensors", "model.bin")
_MIN_TORCH_FOR_BIN = (2, 6, 0)


def embedding_model_dir(model_id: str, cache_dir: str) -> Path:
    """约定本地目录：{cache_dir}/{org}/{name}。"""
    cache = Path(cache_dir)
    if "/" in model_id:
        return cache / model_id
    return cache / model_id.replace(".", "___")


def _find_weight_file(root: Path) -> Optional[Path]:
    """在目录树中查找主模型权重（排除 onnx 导出）。"""
    if not root.is_dir():
        return None
    for name in _WEIGHT_FILENAMES:
        direct = root / name
        if direct.is_file() and direct.stat().st_size > 1_000_000:
            return direct
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix not in (".safetensors", ".bin"):
            continue
        if "onnx" in path.parts:
            continue
        if path.stat().st_size > 1_000_000:
            return path
    return None


def has_model_weights(path: Path) -> bool:
    return _find_weight_file(path) is not None


def has_safetensors_weights(path: Path) -> bool:
    file = path / "model.safetensors"
    return file.is_file() and file.stat().st_size > 1_000_000


def _parse_torch_version(version: str) -> tuple[int, int, int]:
    match = re.match(r"^(\d+)\.(\d+)\.(\d+)", version or "")
    if not match:
        return (0, 0, 0)
    return (int(match.group(1)), int(match.group(2)), int(match.group(3)))


def torch_supports_bin_weights() -> bool:
    try:
        import torch

        return _parse_torch_version(torch.__version__) >= _MIN_TORCH_FOR_BIN
    except Exception:
        return False


def _requires_safetensors(path: Path) -> bool:
    """当仅有 .bin 且 torch<2.6 时，必须切换到 safetensors。"""
    if has_safetensors_weights(path):
        return False
    bin_file = path / "pytorch_model.bin"
    if bin_file.is_file() and bin_file.stat().st_size > 1_000_000:
        return not torch_supports_bin_weights()
    return False


def ensure_safetensors_weight(model_id: str, target: Path) -> None:
    """仅补全 model.safetensors，避免重复下载完整 snapshot。"""
    if has_safetensors_weights(target):
        return
    from huggingface_hub import hf_hub_download

    target.mkdir(parents=True, exist_ok=True)
    logger.warning("尝试补全 model.safetensors: %s", model_id)
    hf_hub_download(
        repo_id=model_id,
        filename="model.safetensors",
        local_dir=str(target),
    )


def _ensure_compatible_weights(model_id: str, target: Path) -> None:
    if not _requires_safetensors(target):
        return
    try:
        ensure_safetensors_weight(model_id, target)
    except Exception as exc:
        try:
            import torch

            torch_ver = torch.__version__
        except Exception:
            torch_ver = "unknown"
        raise RuntimeError(
            f"检测到仅有 pytorch_model.bin，且当前 torch={torch_ver} (<2.6)。"
            "请升级 torch>=2.6 或确保存在 model.safetensors。"
        ) from exc


def is_model_ready(model_id: str | None = None, cache_dir: str | None = None) -> bool:
    mid = (model_id or emb_cfg.DEFAULT_EMBEDDING_MODEL_ID).strip()
    base = (cache_dir or emb_cfg.DEFAULT_EMBEDDING_CACHE_DIR).strip()
    target = embedding_model_dir(mid, base)
    return has_model_weights(target) and not _requires_safetensors(target)


def _download_via_modelscope(model_id: str, cache_dir: str) -> Path:
    from modelscope.hub.snapshot_download import snapshot_download

    cache_dir_path = Path(cache_dir)
    cache_dir_path.mkdir(parents=True, exist_ok=True)
    logger.info("ModelScope 下载 embedding: %s -> %s", model_id, cache_dir)
    downloaded = snapshot_download(model_id=model_id, cache_dir=str(cache_dir_path))
    return Path(downloaded)


def _download_via_huggingface(model_id: str, target: Path) -> Path:
    from huggingface_hub import snapshot_download

    target.mkdir(parents=True, exist_ok=True)
    logger.info("HuggingFace 下载 embedding: %s -> %s", model_id, target)
    snapshot_download(
        repo_id=model_id,
        local_dir=str(target),
        local_dir_use_symlinks=False,
    )
    return target


def ensure_embedding_model(
    model_id: str | None = None,
    cache_dir: str | None = None,
) -> str:
    """
    确保 BAAI/bge-m3 权重完整，返回可用于 SentenceTransformer 的本地目录。
    优先使用 {cache_dir}/BAAI/bge-m3；不完整时依次尝试 ModelScope / HuggingFace 补全。
    """
    mid = (model_id or emb_cfg.DEFAULT_EMBEDDING_MODEL_ID).strip()
    base = (cache_dir or emb_cfg.DEFAULT_EMBEDDING_CACHE_DIR).strip()
    target = embedding_model_dir(mid, base)

    if has_model_weights(target):
        _ensure_compatible_weights(mid, target)
        return str(target.resolve())

    errors: list[str] = []

    try:
        downloaded = _download_via_modelscope(mid, base)
        if has_model_weights(downloaded):
            _ensure_compatible_weights(mid, downloaded)
            return str(downloaded.resolve())
        if has_model_weights(target):
            _ensure_compatible_weights(mid, target)
            return str(target.resolve())
    except Exception as e:
        errors.append(f"ModelScope: {e}")

    try:
        _download_via_huggingface(mid, target)
        if has_model_weights(target):
            _ensure_compatible_weights(mid, target)
            return str(target.resolve())
    except Exception as e:
        errors.append(f"HuggingFace: {e}")

    partial_hint = ""
    if target.is_dir() and any(target.iterdir()):
        partial_hint = f" 目录 {target} 存在但缺少主权重文件（需 model.safetensors 或 pytorch_model.bin）。"
    raise RuntimeError(
        f"无法加载 embedding 模型 {mid}。{partial_hint} "
        f"请运行: python scripts/download_embedding_model.py 。详情: {'; '.join(errors)}"
    )


def check_embedding_runtime() -> None:
    """
    启动加载前校验 transformers / sentence-transformers 依赖链。
    常见失败：torchvision 与 torch 版本不匹配导致 PreTrainedModel 无法导入。
    """
    try:
        import torchvision  # noqa: F401
    except Exception as exc:
        raise RuntimeError(
            "embedding 依赖 torchvision 加载失败（多与 torch 版本不匹配有关）。"
            "请执行: pip install 'torch>=2.6,<2.7' 'torchvision>=0.21,<0.22'"
        ) from exc
    try:
        from transformers import PreTrainedModel  # noqa: F401
    except Exception as exc:
        raise RuntimeError(
            "embedding 依赖 transformers 加载失败（PreTrainedModel 不可用）。"
            "请执行: pip install 'transformers>=4.40,<5' 'torch>=2.6,<2.7' 'torchvision>=0.21,<0.22'"
        ) from exc
    try:
        from sentence_transformers import SentenceTransformer  # noqa: F401
    except Exception as exc:
        raise RuntimeError(
            "embedding 依赖 sentence-transformers 加载失败。"
            "请确认 transformers<5 且与 torch/torchvision 版本匹配。"
        ) from exc


def _load_sentence_model(model_dir: str):
    check_embedding_runtime()
    from sentence_transformers import SentenceTransformer

    kwargs: dict = {"trust_remote_code": True}
    if has_safetensors_weights(Path(model_dir)):
        kwargs["model_kwargs"] = {"use_safetensors": True}
    return SentenceTransformer(model_dir, device="cpu", **kwargs)


def _load_tokenizer(model_dir: str):
    from transformers import AutoTokenizer

    return AutoTokenizer.from_pretrained(model_dir, trust_remote_code=True)


def get_sentence_model(model_id: str | None = None, cache_dir: str | None = None):
    global _sentence_model
    with _model_lock:
        if _sentence_model is None:
            model_dir = ensure_embedding_model(model_id, cache_dir)
            try:
                _sentence_model = _load_sentence_model(model_dir)
            except Exception as exc:
                msg = str(exc)
                if "v2.6" in msg or "CVE-2025-32434" in msg or "torch.load" in msg:
                    mid = (model_id or emb_cfg.DEFAULT_EMBEDDING_MODEL_ID).strip()
                    base = (cache_dir or emb_cfg.DEFAULT_EMBEDDING_CACHE_DIR).strip()
                    target = embedding_model_dir(mid, base)
                    _ensure_compatible_weights(mid, target)
                    _sentence_model = _load_sentence_model(str(target.resolve()))
                else:
                    raise
        return _sentence_model


def get_tokenizer(model_id: str | None = None, cache_dir: str | None = None):
    global _tokenizer
    with _model_lock:
        if _tokenizer is None:
            model_dir = ensure_embedding_model(model_id, cache_dir)
            _tokenizer = _load_tokenizer(model_dir)
        return _tokenizer


def count_tokens(text: str, model_id: str | None = None, cache_dir: str | None = None) -> int:
    text = text or ""
    if not text.strip():
        return 0
    try:
        tok = get_tokenizer(model_id, cache_dir)
        return len(tok.encode(text, add_special_tokens=False))
    except Exception:
        cjk = sum(1 for c in text if "\u4e00" <= c <= "\u9fff")
        other = max(len(text) - cjk, 0)
        return int(cjk / 1.5 + other / 4) + 1


def embed_texts(
    texts: list[str],
    *,
    model_id: str | None = None,
    cache_dir: str | None = None,
    batch_size: int = 32,
) -> np.ndarray:
    if not texts:
        return np.zeros((0, 0), dtype=np.float32)
    model = get_sentence_model(model_id, cache_dir)
    vectors = model.encode(
        texts,
        normalize_embeddings=True,
        show_progress_bar=False,
        batch_size=batch_size,
    )
    return np.asarray(vectors, dtype=np.float32)


def reset_cached_models() -> None:
    """测试或重新下载后清空内存缓存。"""
    global _sentence_model, _tokenizer
    with _model_lock:
        _sentence_model = None
        _tokenizer = None
