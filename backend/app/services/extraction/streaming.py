"""抽取流水线 SSE 流式推送。"""

from __future__ import annotations

import json
import queue
import threading
from collections.abc import Iterator
from typing import Any, Optional

from app.schemas.extraction import PipelineDefaults
from . import pipeline
from .errors import ExtractionCancelled


def request_cancel_event() -> threading.Event:
    return threading.Event()


def iter_extraction_sse_lines(
    source: bytes | str,
    model: str,
    task_description: str,
    *,
    filename: Optional[str] = None,
    defaults: Optional[PipelineDefaults] = None,
    cancel_event: threading.Event | None = None,
) -> Iterator[str]:
    cancel = cancel_event or threading.Event()
    event_queue: queue.Queue[dict[str, Any] | None] = queue.Queue()

    def emit(event: dict[str, Any]) -> None:
        if cancel.is_set():
            return
        event_queue.put(event)

    def worker() -> None:
        try:
            if cancel.is_set():
                return
            pipeline.run_document_extraction(
                source=source,
                model=model,
                task_description=task_description,
                filename=filename,
                defaults=defaults,
                emit=emit,
                cancel_event=cancel,
            )
        except ExtractionCancelled as exc:
            event_queue.put({"type": "cancelled", "message": str(exc)})
        except Exception as exc:
            if not cancel.is_set():
                event_queue.put({"type": "error", "message": str(exc)})
        finally:
            event_queue.put(None)

    threading.Thread(target=worker, daemon=True).start()

    poll_sec = 0.25
    while True:
        try:
            item = event_queue.get(timeout=poll_sec)
        except queue.Empty:
            if cancel.is_set():
                break
            continue
        if item is None:
            break
        yield f"data: {json.dumps(item, ensure_ascii=False)}\n\n"
        if cancel.is_set() and item.get("type") in ("cancelled", "error"):
            break
