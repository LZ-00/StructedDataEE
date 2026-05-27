from unittest.mock import patch

import numpy as np

from app.schemas.extraction import PipelineDefaults
from app.services.extraction import semantic_chunker


def test_split_natural_fragments_heading_and_sentences():
    text = "1. Introduction\n\nLaser welding is widely used. It improves efficiency.\n\n2. Methods\n\nThe samples were prepared."
    frags = semantic_chunker.split_natural_fragments(text)
    assert len(frags) >= 4
    headings = [f for f in frags if f.boundary_type == "heading"]
    assert any("Introduction" in h.text for h in headings)


def test_chunk_short_text_single_block():
    text = "短文本块。"
    cfg = PipelineDefaults(min_chunk_chars=80, min_chunk_tokens=10, max_chunk_tokens=1200)
    with patch.object(semantic_chunker.embedding_loader, "ensure_embedding_model"):
        chunks, warnings = semantic_chunker.chunk_text(
            text, defaults=cfg, document_name="demo.txt"
        )
    assert len(chunks) == 1
    assert chunks[0].document_name == "demo.txt"


def test_chunk_with_mock_embeddings():
    text = (
        "1. Materials\n\n"
        "Ti-6Al-4V alloy was used in this study. The composition was verified by XRD.\n\n"
        "2. Synthesis\n\n"
        "Powder bed fusion was performed at 800 W. The scan speed was 600 mm/s."
    )
    frags = semantic_chunker.split_natural_fragments(text)
    assert len(frags) >= 3
    n = len(frags)
    emb = np.zeros((n, 8), dtype=np.float32)
    for i in range(n):
        emb[i, i % 8] = 1.0

    cfg = PipelineDefaults(
        min_chunk_tokens=10,
        max_chunk_tokens=500,
        similarity_threshold=0.5,
        embedding_model="BAAI/bge-m3",
        embedding_cache_dir="/data/lz/modelscope/embedding",
    )

    with patch.object(semantic_chunker.embedding_loader, "ensure_embedding_model", return_value="/tmp/bge-m3"):
        with patch.object(semantic_chunker.embedding_loader, "embed_texts", return_value=emb):
            with patch.object(semantic_chunker.embedding_loader, "count_tokens", side_effect=lambda t, *_a, **_k: max(1, len(t) // 4)):
                chunks, warnings = semantic_chunker.chunk_text(
                    text, document_name="paper.pdf", defaults=cfg
                )
    assert len(chunks) >= 1
    assert chunks[0].document_name == "paper.pdf"
    assert chunks[0].token_count >= 1
    assert not any("回退" in w for w in warnings)


def test_chunk_fallback_on_embed_failure():
    text = "段落一内容足够长。" * 5 + "\n\n" + "段落二另一主题内容。" * 5
    cfg = PipelineDefaults(min_chunk_tokens=10, max_chunk_tokens=1200)

    def fail(*_a, **_k):
        raise RuntimeError("mock embed fail")

    with patch.object(semantic_chunker.embedding_loader, "ensure_embedding_model", side_effect=fail):
        chunks, warnings = semantic_chunker.chunk_text(text, defaults=cfg)
    assert len(chunks) >= 1
    assert any("回退" in w for w in warnings)
