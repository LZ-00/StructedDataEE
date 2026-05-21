import asyncio

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.api.deps import get_current_user
from app.services import evaluation_generation, evaluation_service

router = APIRouter()


@router.get("/options")
def options(_user: str = Depends(get_current_user)) -> dict:
    return evaluation_service.get_evaluation_options()


class EvaluationRequest(BaseModel):
    model: str
    groundTruth: str


@router.post("/evaluate/stream")
async def evaluate_stream(
    request: Request,
    body: EvaluationRequest,
    _user: str = Depends(get_current_user),
) -> StreamingResponse:
    """SSE 流式评估：实时推送运行日志与 CoT 推理文本。"""
    cancel_event = evaluation_generation.request_cancel_event()

    async def event_stream():
        sync_gen = evaluation_generation.iter_sse_lines(
            body.model,
            body.groundTruth,
            cancel_event=cancel_event,
        )

        def pull_line() -> str | None:
            try:
                return next(sync_gen)
            except StopIteration:
                return None

        while True:
            if await request.is_disconnected():
                cancel_event.set()
            line = await asyncio.to_thread(pull_line)
            if line is None:
                break
            yield line
            if cancel_event.is_set():
                break

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
