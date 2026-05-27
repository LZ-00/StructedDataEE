"""文档抽取流水线编排：解析 → 分块 → 相关性筛选 → 结构化抽取。"""

from __future__ import annotations

import threading
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from typing import Any, Callable, Optional

from app.schemas.extraction import (
    DocumentExtractionResponse,
    DocumentMeta,
    ExtractionItem,
    PipelineDefaults,
    RelevanceResult,
    TextChunk,
)
from . import document_loader, record_merger, relevance_filter, semantic_chunker, structured_extractor
from .errors import ExtractionCancelled

EmitFn = Callable[[dict[str, Any]], None]

EXTRACTION_STEPS = [
    {"title": "解析文档", "description": "加载 PDF/TXT 或纯文本"},
    {"title": "语义分块", "description": "BGE-M3 嵌入相邻合并"},
    {"title": "相关性筛选", "description": "LLM 判断各块与任务相关性"},
    {"title": "结构化抽取", "description": "从相关块抽取材料字段"},
]


def _step(emit: EmitFn | None, index: int, status: str) -> None:
    if emit:
        emit({"type": "step", "index": index, "status": status})


def _stage(emit: EmitFn | None, stage: str, message: str) -> None:
    if emit:
        emit({"type": "stage", "stage": stage, "message": message})


def _ensure_not_cancelled(cancel_event: threading.Event | None) -> None:
    if cancel_event and cancel_event.is_set():
        raise ExtractionCancelled("用户已中止抽取")


def _cancel_futures(futures: list[Future[Any]]) -> None:
    for fut in futures:
        fut.cancel()


def run_document_extraction(
    source: bytes | str,
    model: str,
    task_description: str,
    *,
    filename: Optional[str] = None,
    defaults: Optional[PipelineDefaults] = None,
    emit: EmitFn | None = None,
    cancel_event: threading.Event | None = None,
) -> dict[str, Any]:
    """
    执行完整抽取流水线。
    source 为 bytes 时按 filename 解析文档；为 str 时视为已解析纯文本。
    emit 非空时通过 SSE 事件推送阶段与块级进度。
    cancel_event 置位后尽快中止后续分块 / LLM 调用。
    """
    cfg = defaults or PipelineDefaults()
    warnings: list[str] = []

    _ensure_not_cancelled(cancel_event)

    if emit:
        emit({"type": "step_init", "steps": EXTRACTION_STEPS})

    _step(emit, 0, "process")
    _stage(emit, "parsing", "正在解析文档…")

    if isinstance(source, bytes):
        text, load_warnings = document_loader.load_document(source, filename)
        warnings.extend(load_warnings)
        meta_filename = filename
    else:
        text = (source or "").strip()
        if not text:
            raise ValueError("待抽取文本为空")
        meta_filename = filename

    _ensure_not_cancelled(cancel_event)

    if emit:
        emit(
            {
                "type": "parsed",
                "total_chars": len(text),
                "filename": meta_filename,
            }
        )

    _step(emit, 0, "finish")
    _step(emit, 1, "process")
    _stage(emit, "chunking", "正在进行语义分块（BGE-M3）…")

    chunks, chunk_warnings = semantic_chunker.chunk_text(
        text,
        document_name=meta_filename,
        defaults=cfg,
        cancel_event=cancel_event,
    )
    warnings.extend(chunk_warnings)

    _ensure_not_cancelled(cancel_event)

    if emit:
        emit(
            {
                "type": "chunked",
                "chunk_count": len(chunks),
                "chunks": [_chunk_preview(c) for c in chunks],
            }
        )

    _step(emit, 1, "finish")

    if not chunks:
        response = DocumentExtractionResponse(
            document_meta=DocumentMeta(
                filename=meta_filename,
                total_chars=len(text),
                chunk_count=0,
                relevant_count=0,
                warnings=warnings,
            ),
            items=[],
            records=[],
        )
        result = response.model_dump()
        if emit:
            emit({"type": "done", "result": result})
        return result

    _step(emit, 2, "process")
    _stage(emit, "relevance", f"正在对 {len(chunks)} 个文本块做相关性判断…")

    relevance_map = _assess_all_chunks(
        chunks,
        task_description,
        model,
        cfg.llm_concurrency,
        emit=emit,
        cancel_event=cancel_event,
    )
    relevant_chunks = [c for c in chunks if relevance_map[c.chunk_id].is_relevant]

    _ensure_not_cancelled(cancel_event)

    _step(emit, 2, "finish")
    _step(emit, 3, "process")
    _stage(
        emit,
        "extracting",
        f"正在从 {len(relevant_chunks)} 个相关块抽取结构化数据…",
    )

    items = _extract_all_relevant(
        relevant_chunks,
        relevance_map,
        task_description,
        model,
        cfg.llm_concurrency,
        warnings,
        emit=emit,
        cancel_event=cancel_event,
    )

    _ensure_not_cancelled(cancel_event)

    _step(emit, 3, "finish")

    items, flat_records, _merge_stats = record_merger.merge_records(relevant_chunks, items)

    response = DocumentExtractionResponse(
        document_meta=DocumentMeta(
            filename=meta_filename,
            total_chars=len(text),
            chunk_count=len(chunks),
            relevant_count=len(relevant_chunks),
            warnings=warnings,
        ),
        items=items,
        records=flat_records,
    )
    result = response.model_dump()
    if emit:
        emit({"type": "done", "result": result})
    return result


def _chunk_preview(chunk: TextChunk) -> dict[str, Any]:
    return {
        "chunk_id": chunk.chunk_id,
        "text": chunk.text,
        "document_name": chunk.document_name,
        "chapter": chunk.chapter,
        "paragraph_index": chunk.paragraph_index,
        "language": chunk.language,
        "token_count": chunk.token_count,
        "status": "pending",
    }


def _assess_all_chunks(
    chunks: list[TextChunk],
    task_description: str,
    model: str,
    max_workers: int,
    *,
    emit: EmitFn | None = None,
    cancel_event: threading.Event | None = None,
) -> dict[str, RelevanceResult]:
    results: dict[str, RelevanceResult] = {}
    index_by_id = {ch.chunk_id: i for i, ch in enumerate(chunks)}
    total = len(chunks)

    def work(ch: TextChunk) -> tuple[str, RelevanceResult]:
        _ensure_not_cancelled(cancel_event)
        return ch.chunk_id, relevance_filter.assess_relevance(ch, task_description, model)

    with ThreadPoolExecutor(max_workers=max(1, max_workers)) as pool:
        futures = [pool.submit(work, ch) for ch in chunks]
        try:
            for fut in as_completed(futures):
                _ensure_not_cancelled(cancel_event)
                chunk_id, rel = fut.result()
                results[chunk_id] = rel
                if emit:
                    emit(
                        {
                            "type": "relevance_done",
                            "chunk_id": chunk_id,
                            "index": index_by_id.get(chunk_id, 0),
                            "total": total,
                            "is_relevant": rel.is_relevant,
                            "reason": rel.reason,
                        }
                    )
        except ExtractionCancelled:
            _cancel_futures(futures)
            raise

    return results


def _extract_all_relevant(
    chunks: list[TextChunk],
    relevance_map: dict[str, RelevanceResult],
    task_description: str,
    model: str,
    max_workers: int,
    warnings: list[str],
    *,
    emit: EmitFn | None = None,
    cancel_event: threading.Event | None = None,
) -> list[ExtractionItem]:
    items: list[ExtractionItem] = []
    index_by_id = {ch.chunk_id: i for i, ch in enumerate(chunks)}
    total = len(chunks)

    def work(ch: TextChunk) -> ExtractionItem:
        _ensure_not_cancelled(cancel_event)
        rel = relevance_map[ch.chunk_id]
        if emit:
            emit(
                {
                    "type": "extract_start",
                    "chunk_id": ch.chunk_id,
                    "index": index_by_id.get(ch.chunk_id, 0),
                    "total": total,
                }
            )
        try:
            records = structured_extractor.extract_records(ch.text, task_description, model)
            item = ExtractionItem(
                chunk_id=ch.chunk_id,
                source_text=ch.text,
                relevance=rel,
                records=records,
            )
        except Exception as e:
            warnings.append(f"块 {ch.chunk_id} 抽取失败: {e}")
            item = ExtractionItem(
                chunk_id=ch.chunk_id,
                source_text=ch.text,
                relevance=rel,
                records=[],
                error=str(e),
            )
        return item

    if not chunks:
        return items

    with ThreadPoolExecutor(max_workers=max(1, max_workers)) as pool:
        futures = [pool.submit(work, ch) for ch in chunks]
        try:
            for fut in as_completed(futures):
                _ensure_not_cancelled(cancel_event)
                item = fut.result()
                items.append(item)
                if emit:
                    emit({"type": "item", "item": item.model_dump()})
        except ExtractionCancelled:
            _cancel_futures(futures)
            raise

    items.sort(key=lambda x: x.chunk_id)
    return items
