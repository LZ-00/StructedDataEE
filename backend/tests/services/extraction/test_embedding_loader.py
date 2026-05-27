from pathlib import Path
from unittest.mock import patch

import pytest

from app.config import embedding_catalog as emb_cfg
from app.services.extraction import embedding_loader


def test_embedding_model_dir():
    p = embedding_loader.embedding_model_dir("BAAI/bge-m3", "/data/lz/modelscope/embedding")
    assert p == Path("/data/lz/modelscope/embedding/BAAI/bge-m3")


def test_is_model_ready_false_when_missing(tmp_path):
    assert not embedding_loader.is_model_ready("BAAI/bge-m3", str(tmp_path))


def test_is_model_ready_false_with_config_only(tmp_path):
    model_dir = tmp_path / "BAAI" / "bge-m3"
    model_dir.mkdir(parents=True)
    (model_dir / "config.json").write_text("{}", encoding="utf-8")
    assert not embedding_loader.is_model_ready("BAAI/bge-m3", str(tmp_path))


def test_ensure_embedding_uses_existing_dir(tmp_path):
    model_dir = tmp_path / "BAAI" / "bge-m3"
    model_dir.mkdir(parents=True)
    (model_dir / "config.json").write_text("{}", encoding="utf-8")
    (model_dir / "model.safetensors").write_bytes(b"x" * 2_000_000)
    path = embedding_loader.ensure_embedding_model("BAAI/bge-m3", str(tmp_path))
    assert path == str(model_dir.resolve())


def test_has_safetensors_weights(tmp_path):
    model_dir = tmp_path / "BAAI" / "bge-m3"
    model_dir.mkdir(parents=True)
    (model_dir / "model.safetensors").write_bytes(b"x" * 2_000_000)
    assert embedding_loader.has_safetensors_weights(model_dir)


def test_is_model_ready_false_when_only_bin_and_old_torch(tmp_path):
    model_dir = tmp_path / "BAAI" / "bge-m3"
    model_dir.mkdir(parents=True)
    (model_dir / "pytorch_model.bin").write_bytes(b"x" * 2_000_000)
    with patch("app.services.extraction.embedding_loader.torch_supports_bin_weights", return_value=False):
        assert not embedding_loader.is_model_ready("BAAI/bge-m3", str(tmp_path))


def test_check_embedding_runtime_passes_or_skips():
    try:
        embedding_loader.check_embedding_runtime()
    except RuntimeError:
        pytest.skip("embedding runtime dependencies not installed in CI")
