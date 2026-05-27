#!/usr/bin/env python3
"""下载 BAAI/bge-m3 至 /data/lz/modelscope/embedding（需完整 pytorch/safetensors 权重）。"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.config import embedding_catalog as emb_cfg
from app.services.extraction.embedding_loader import (
    ensure_embedding_model,
    has_model_weights,
    has_safetensors_weights,
    ensure_safetensors_weight,
    torch_supports_bin_weights,
    embedding_model_dir,
    reset_cached_models,
)


def main() -> int:
    model_id = emb_cfg.DEFAULT_EMBEDDING_MODEL_ID
    cache_dir = emb_cfg.DEFAULT_EMBEDDING_CACHE_DIR
    target = embedding_model_dir(model_id, cache_dir)

    print(f"模型: {model_id}")
    print(f"目标目录: {target}")
    print(f"torch 支持加载 .bin: {torch_supports_bin_weights()}")

    if has_model_weights(target):
        print("检测到完整权重，跳过下载。")
    else:
        print("权重不完整或缺失，开始下载（ModelScope / HuggingFace）…")

    if not has_safetensors_weights(target) and not torch_supports_bin_weights():
        try:
            ensure_safetensors_weight(model_id, target)
            print("已补全 model.safetensors。")
        except Exception as e:
            print(f"补全 model.safetensors 失败，继续常规流程: {e}")

    reset_cached_models()
    path = ensure_embedding_model(model_id, cache_dir)
    weight = has_model_weights(Path(path))
    has_st = has_safetensors_weights(Path(path))
    print(f"就绪: {path}")
    print(f"权重校验: {'通过' if weight else '失败'}")
    print(f"safetensors: {'存在' if has_st else '不存在'}")
    return 0 if weight else 1


if __name__ == "__main__":
    raise SystemExit(main())
