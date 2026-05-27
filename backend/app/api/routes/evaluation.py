import asyncio

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse

from app.api.deps import get_current_user
from app.services import model_config_service
from app.services.evaluate import service as evaluate_service

router = APIRouter()
_DEFAULT_EVALUATION_MODEL = model_config_service.get_default_model_id("evaluation")


@router.get("/options")
def options(_user: str = Depends(get_current_user)) -> dict:
    models = model_config_service.get_select_options(usage="evaluation")
    return evaluate_service.get_evaluation_options(models)


@router.post("/evaluate/stream")
async def evaluate_stream(
    request: Request,
    file: UploadFile = File(...),
    model: str = Form(_DEFAULT_EVALUATION_MODEL),
    _user: str = Depends(get_current_user),
) -> StreamingResponse:
    """SSE 流式评估：实时推送运行日志与 CoT 推理文本。"""
    raw = await file.read()
    try:
        samples = evaluate_service.build_uploaded_samples(raw, file.filename)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    cancel_event = evaluate_service.request_cancel_event()

    async def event_stream():
        sync_gen = evaluate_service.iter_sse_lines(
            model=model,
            raw=raw,
            filename=file.filename,
            samples=samples,
            cancel_event=cancel_event,
        )

        def pull_line() -> str | None:
            try:
                return next(sync_gen)
            except StopIteration:
                return None

        try:
            while True:
                if await request.is_disconnected():
                    cancel_event.set()
                    break
                line = await asyncio.to_thread(pull_line)
                if line is None:
                    break
                yield line
                if cancel_event.is_set():
                    break
        finally:
            cancel_event.set()

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
