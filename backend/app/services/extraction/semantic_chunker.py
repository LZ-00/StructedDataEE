"""科研论文语义分块：自然边界切分 + BGE-M3 相邻相似度合并。"""

from __future__ import annotations

import re
import threading
from dataclasses import dataclass
from typing import Optional

import numpy as np

from app.config import embedding_catalog as emb_cfg
from app.schemas.extraction import PipelineDefaults, TextChunk
from app.services.extraction import embedding_loader
from app.services.extraction.errors import ExtractionCancelled

# 章节/标题行
_HEADING_RE = re.compile(
    r"^(?:"
    r"\d+(?:\.\d+)*[.)]?\s+\S.+|"
    r"第[一二三四五六七八九十百千\d]+[章节部分篇]\s*\S*|"
    r"(?:Abstract|Introduction|Background|Methods?|Materials?|Results?|Discussion|Conclusion|References|Appendix)\b\S*|"
    r"#{1,6}\s+\S.+|"
    r"[一二三四五六七八九十]+[、．.]\s*\S+"
    r")$",
    re.IGNORECASE,
)

# 列表项
_LIST_ITEM_RE = re.compile(
    r"^(?:[-*•●]\s+|\(\d+\)\s+|\d+[.)]\s+|[（(]\d+[）)]\s+)"
)

# 公式说明块（行内/块级公式、图注式）
_FORMULA_LINE_RE = re.compile(
    r"(?:^\s*\$\$.+\$\$\s*$|^\s*\$.+\$\s*$|^\s*\\\[.+\\\]\s*$|^\s*\\begin\{equation)"
)

# 自然边界：句号、分号、换行等
_BOUNDARY_SPLIT_RE = re.compile(
    r"(?<=[。！？.!?;；:：])\s+|(?<=\n)"
)

_DEFAULTS = PipelineDefaults()


@dataclass
class _Fragment:
    text: str
    start_offset: int
    end_offset: int
    chapter: str = ""
    paragraph_index: int = 0
    fragment_index: int = 0
    language: str = "mixed"
    boundary_type: str = "sentence"


def detect_language(text: str) -> str:
    if not text.strip():
        return "mixed"
    cjk = sum(1 for c in text if "\u4e00" <= c <= "\u9fff")
    latin = sum(1 for c in text if c.isascii() and c.isalpha())
    if cjk >= latin * 2 and cjk > 0:
        return "zh"
    if latin >= cjk * 2 and latin > 0:
        return "en"
    return "mixed"


def _is_heading(line: str) -> bool:
    s = line.strip()
    if len(s) < 2 or len(s) > 200:
        return False
    return bool(_HEADING_RE.match(s))


def _split_line_to_fragments(
    line: str,
    line_start: int,
    chapter: str,
    paragraph_index: int,
    boundary_type: str,
) -> list[_Fragment]:
    line = line.rstrip()
    if not line.strip():
        return []

    if _is_heading(line):
        return [
            _Fragment(
                text=line.strip(),
                start_offset=line_start,
                end_offset=line_start + len(line),
                chapter=line.strip(),
                paragraph_index=paragraph_index,
                boundary_type="heading",
                language=detect_language(line),
            )
        ]

    if _LIST_ITEM_RE.match(line.strip()) or _FORMULA_LINE_RE.search(line):
        return [
            _Fragment(
                text=line.strip(),
                start_offset=line_start,
                end_offset=line_start + len(line),
                chapter=chapter,
                paragraph_index=paragraph_index,
                boundary_type="list" if _LIST_ITEM_RE.match(line.strip()) else "formula",
                language=detect_language(line),
            )
        ]

    parts = _BOUNDARY_SPLIT_RE.split(line)
    frags: list[_Fragment] = []
    cursor = line_start
    for part in parts:
        s = part.strip()
        if len(s) < 2:
            cursor += len(part)
            continue
        frags.append(
            _Fragment(
                text=s,
                start_offset=cursor,
                end_offset=cursor + len(part),
                chapter=chapter,
                paragraph_index=paragraph_index,
                boundary_type=boundary_type,
                language=detect_language(s),
            )
        )
        cursor += len(part)
    return frags


def split_natural_fragments(full_text: str) -> list[_Fragment]:
    """
    按自然边界切分为最小片段：标题、段落、句号、换行、列表、公式说明等。
    """
    text = (full_text or "").replace("\r\n", "\n").replace("\r", "\n")
    if not text.strip():
        return []

    fragments: list[_Fragment] = []
    current_chapter = ""
    paragraph_index = 0

    # 先按空行分段落
    para_blocks = re.split(r"\n{2,}", text)
    search_from = 0

    for block in para_blocks:
        block = block.strip()
        if not block:
            continue
        block_start = text.find(block, search_from)
        if block_start < 0:
            block_start = search_from
        search_from = block_start + len(block)

        lines = block.split("\n")
        line_cursor = block_start
        for line in lines:
            if _is_heading(line.strip()):
                current_chapter = line.strip()
                paragraph_index = 0

            line_frags = _split_line_to_fragments(
                line,
                line_cursor,
                current_chapter,
                paragraph_index,
                boundary_type="paragraph" if "\n" not in line else "line",
            )
            for i, frag in enumerate(line_frags):
                frag.fragment_index = len(fragments) + i
                fragments.append(frag)
            if line.strip():
                paragraph_index += 1
            line_cursor += len(line) + 1

    # 去重/合并过短碎片到前一片段（同一段落内）
    merged: list[_Fragment] = []
    for frag in fragments:
        if merged and len(frag.text) < 8 and merged[-1].paragraph_index == frag.paragraph_index:
            prev = merged[-1]
            merged[-1] = _Fragment(
                text=f"{prev.text} {frag.text}".strip(),
                start_offset=prev.start_offset,
                end_offset=frag.end_offset,
                chapter=prev.chapter or frag.chapter,
                paragraph_index=prev.paragraph_index,
                fragment_index=prev.fragment_index,
                boundary_type=prev.boundary_type,
                language=detect_language(f"{prev.text} {frag.text}"),
            )
        else:
            merged.append(frag)

    for i, f in enumerate(merged):
        f.fragment_index = i
    return merged


def _cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
    if a.size == 0 or b.size == 0:
        return 1.0
    return float(np.dot(a, b))


def _merge_fragments_by_similarity(
    fragments: list[_Fragment],
    embeddings: np.ndarray,
    cfg: PipelineDefaults,
) -> list[list[int]]:
    """按相邻相似度合并片段索引组；相似度骤降或超长则断开。"""
    if not fragments:
        return []
    if len(fragments) == 1:
        return [[0]]

    groups: list[list[int]] = [[0]]
    prev_sim = 1.0

    for i in range(1, len(fragments)):
        sim = _cosine_sim(embeddings[i - 1], embeddings[i])
        group = groups[-1]
        group_text = "\n".join(fragments[j].text for j in group)
        cand_text = f"{group_text}\n{fragments[i].text}"
        group_tokens = embedding_loader.count_tokens(
            group_text, cfg.embedding_model, cfg.embedding_cache_dir
        )
        cand_tokens = embedding_loader.count_tokens(
            cand_text, cfg.embedding_model, cfg.embedding_cache_dir
        )

        sim_drop = prev_sim - sim >= cfg.similarity_drop_delta
        low_sim = sim < cfg.similarity_threshold
        heading_break = fragments[i].boundary_type == "heading"
        too_long = cand_tokens > cfg.max_chunk_tokens

        if heading_break or low_sim or sim_drop or too_long:
            groups.append([i])
        else:
            group.append(i)

        prev_sim = sim

    return groups


def _enforce_token_limits(
    fragments: list[_Fragment],
    groups: list[list[int]],
    cfg: PipelineDefaults,
) -> list[list[int]]:
    """合并后按 token 上限拆分组，并尝试合并过短的相邻组。"""
    refined: list[list[int]] = []
    for group in groups:
        if not group:
            continue
        buf: list[int] = []
        for idx in group:
            buf.append(idx)
            body = "\n".join(fragments[j].text for j in buf)
            tokens = embedding_loader.count_tokens(
                body, cfg.embedding_model, cfg.embedding_cache_dir
            )
            if tokens > cfg.max_chunk_tokens and len(buf) > 1:
                refined.append(buf[:-1])
                buf = [idx]
        if buf:
            refined.append(buf)

    merged: list[list[int]] = []
    for group in refined:
        if not merged:
            merged.append(group)
            continue
        prev_body = "\n".join(fragments[j].text for j in merged[-1])
        cur_body = "\n".join(fragments[j].text for j in group)
        combined = f"{prev_body}\n{cur_body}"
        combined_tokens = embedding_loader.count_tokens(
            combined, cfg.embedding_model, cfg.embedding_cache_dir
        )
        if combined_tokens <= cfg.max_chunk_tokens and embedding_loader.count_tokens(
            prev_body, cfg.embedding_model, cfg.embedding_cache_dir
        ) < cfg.min_chunk_tokens:
            merged[-1] = merged[-1] + group
        else:
            merged.append(group)
    return merged


def _groups_to_chunks(
    fragments: list[_Fragment],
    groups: list[list[int]],
    document_name: Optional[str],
    cfg: PipelineDefaults,
) -> list[TextChunk]:
    chunks: list[TextChunk] = []
    for i, group in enumerate(groups, start=1):
        texts = [fragments[j].text for j in group]
        body = "\n".join(texts)
        start = min(fragments[j].start_offset for j in group)
        end = max(fragments[j].end_offset for j in group)
        chapters = [fragments[j].chapter for j in group if fragments[j].chapter]
        chapter = chapters[-1] if chapters else (fragments[group[0]].chapter or "")
        para_idx = fragments[group[0]].paragraph_index
        langs = {fragments[j].language for j in group}
        language = langs.pop() if len(langs) == 1 else "mixed"
        token_count = embedding_loader.count_tokens(
            body, cfg.embedding_model, cfg.embedding_cache_dir
        )
        chunks.append(
            TextChunk(
                chunk_id=f"c-{i:03d}",
                text=body,
                start_offset=start,
                end_offset=end,
                document_name=document_name,
                chapter=chapter or None,
                paragraph_index=para_idx,
                language=language,
                token_count=token_count,
            )
        )
    return chunks


def _chunk_by_paragraphs_fallback(
    text: str,
    document_name: Optional[str],
    cfg: PipelineDefaults,
) -> list[TextChunk]:
    paragraphs = [p.strip() for p in re.split(r"\n{2,}", text) if p.strip()]
    if not paragraphs:
        paragraphs = [text]
    chunks: list[TextChunk] = []
    buf: list[str] = []
    buf_tokens = 0
    for para in paragraphs:
        pt = embedding_loader.count_tokens(para, cfg.embedding_model, cfg.embedding_cache_dir)
        if buf and buf_tokens + pt > cfg.max_chunk_tokens:
            body = "\n\n".join(buf)
            chunks.append(
                TextChunk(
                    chunk_id=f"c-{len(chunks)+1:03d}",
                    text=body,
                    document_name=document_name,
                    language=detect_language(body),
                    token_count=buf_tokens,
                )
            )
            buf = [para]
            buf_tokens = pt
        else:
            buf.append(para)
            buf_tokens += pt
    if buf:
        body = "\n\n".join(buf)
        chunks.append(
            TextChunk(
                chunk_id=f"c-{len(chunks)+1:03d}",
                text=body,
                document_name=document_name,
                language=detect_language(body),
                token_count=buf_tokens,
            )
        )
    return chunks


def _ensure_not_cancelled(cancel_event: threading.Event | None) -> None:
    if cancel_event and cancel_event.is_set():
        raise ExtractionCancelled("用户已中止抽取")


def chunk_text(
    full_text: str,
    *,
    document_name: Optional[str] = None,
    defaults: Optional[PipelineDefaults] = None,
    cancel_event: threading.Event | None = None,
) -> tuple[list[TextChunk], list[str]]:
    """
    科研论文语义分块：
    1. 自然边界切分最小片段
    2. BGE-M3 embedding
    3. 相邻相似度合并 / 骤降断开
    4. 控制 800–1200 tokens
    """
    cfg = defaults or _DEFAULTS
    warnings: list[str] = []
    text = (full_text or "").strip()
    if not text:
        return [], warnings

    _ensure_not_cancelled(cancel_event)

    fragments = split_natural_fragments(text)
    if not fragments:
        return [], warnings
    if len(fragments) == 1:
        f = fragments[0]
        tc = embedding_loader.count_tokens(f.text, cfg.embedding_model, cfg.embedding_cache_dir)
        return [
            TextChunk(
                chunk_id="c-001",
                text=f.text,
                start_offset=f.start_offset,
                end_offset=f.end_offset,
                document_name=document_name,
                chapter=f.chapter or None,
                paragraph_index=f.paragraph_index,
                language=f.language,
                token_count=tc,
            )
        ], warnings

    _ensure_not_cancelled(cancel_event)

    try:
        embedding_loader.ensure_embedding_model(cfg.embedding_model, cfg.embedding_cache_dir)
        _ensure_not_cancelled(cancel_event)
        texts = [f.text for f in fragments]
        embeddings = embedding_loader.embed_texts(
            texts,
            model_id=cfg.embedding_model,
            cache_dir=cfg.embedding_cache_dir,
        )
    except ExtractionCancelled:
        raise
    except Exception as e:
        hint = str(e)
        if "PreTrainedModel" in hint or "torchvision" in hint:
            hint += (
                "（多为 torch/torchvision/transformers 版本不匹配；"
                "建议: pip install 'torch>=2.6,<2.7' 'torchvision>=0.21,<0.22' 'transformers>=4.40,<5'）"
            )
        warnings.append(f"BGE-M3 embedding 不可用，已回退为段落分块: {hint}")
        return _chunk_by_paragraphs_fallback(text, document_name, cfg), warnings

    _ensure_not_cancelled(cancel_event)

    groups = _merge_fragments_by_similarity(fragments, embeddings, cfg)
    groups = _enforce_token_limits(fragments, groups, cfg)

    if len(groups) > cfg.max_chunks:
        warnings.append(f"文本块数量超过上限 {cfg.max_chunks}，已合并相邻块")
        while len(groups) > cfg.max_chunks and len(groups) > 1:
            _ensure_not_cancelled(cancel_event)
            merged = []
            i = 0
            while i < len(groups):
                if i + 1 < len(groups):
                    merged.append(groups[i] + groups[i + 1])
                    i += 2
                else:
                    merged.append(groups[i])
                    i += 1
            groups = merged

    chunks = _groups_to_chunks(fragments, groups, document_name, cfg)
    return chunks, warnings


# 兼容旧测试：保留 split_sentences 名称
def split_sentences(text: str) -> list[str]:
    return [f.text for f in split_natural_fragments(text)]
