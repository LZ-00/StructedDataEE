import asyncio

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.api.deps import get_current_user
from app.services import extraction_service, model_config_service
from app.services.extraction import streaming as extraction_streaming

router = APIRouter()

_DEFAULT_EXTRACTION_MODEL = model_config_service.get_default_model_id("extraction")


@router.get("/options")
def options(_user: str = Depends(get_current_user)) -> dict:
    return extraction_service.get_workspace_options()


@router.post("/extract")
async def extract(
    _user: str = Depends(get_current_user),
    file: UploadFile = File(...),
    model: str = Form(_DEFAULT_EXTRACTION_MODEL),
    task_description: str = Form(""),
) -> dict:
    raw = await file.read()
    try:
        return extraction_service.run_extraction_from_file(raw, file.filename, model, task_description)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/extract/stream")
async def extract_stream(
    request: Request,
    _user: str = Depends(get_current_user),
    file: UploadFile = File(...),
    model: str = Form(_DEFAULT_EXTRACTION_MODEL),
    task_description: str = Form(""),
) -> StreamingResponse:
    """SSE 流式抽取：推送分块列表与各块相关性/抽取进度。"""
    raw = await file.read()
    cancel_event = extraction_streaming.request_cancel_event()

    async def event_stream():
        sync_gen = extraction_streaming.iter_extraction_sse_lines(
            source=raw,
            model=model,
            task_description=task_description,
            filename=file.filename,
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


class ExtractTextRequest(BaseModel):
    text: str
    model: str = _DEFAULT_EXTRACTION_MODEL
    task_description: str = ""


@router.post("/extract-text")
def extract_text(body: ExtractTextRequest, _user: str = Depends(get_current_user)) -> dict:
    try:
        return extraction_service.run_extraction(body.text, body.model, body.task_description)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/extract-text/stream")
async def extract_text_stream(
    request: Request,
    body: ExtractTextRequest,
    _user: str = Depends(get_current_user),
) -> StreamingResponse:
    """SSE 流式文本抽取。"""
    cancel_event = extraction_streaming.request_cancel_event()

    async def event_stream():
        sync_gen = extraction_streaming.iter_extraction_sse_lines(
            source=body.text,
            model=body.model,
            task_description=body.task_description,
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
