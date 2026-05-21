"""LoRA 微调 SSE 事件流。"""

from __future__ import annotations

import json
import queue
import threading
from collections.abc import Iterator
from typing import Any

from app.finetune import catalog as ft_catalog
from app.finetune.config import FineTuneParams
from app.finetune.pipeline import run_lora_finetune


def iter_sse_lines(body: dict[str, Any]) -> Iterator[str]:
    params = FineTuneParams.from_request(body)
    yield f"data: {json.dumps({'type': 'step_init', 'steps': ft_catalog.FINETUNE_STEPS}, ensure_ascii=False)}\n\n"

    event_queue: queue.Queue[dict[str, Any] | None] = queue.Queue()

    def emit(event: dict[str, Any]) -> None:
        event_queue.put(event)

    def worker() -> None:
        try:
            result = run_lora_finetune(params, emit=emit)
            event_queue.put({"type": "done", "result": result})
        except Exception as exc:
            event_queue.put({"type": "error", "message": str(exc)})
        finally:
            event_queue.put(None)

    threading.Thread(target=worker, daemon=True).start()

    while True:
        item = event_queue.get()
        if item is None:
            break
        yield f"data: {json.dumps(item, ensure_ascii=False)}\n\n"
