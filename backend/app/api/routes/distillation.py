import asyncio
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel, Field

from app.api.deps import get_current_user
from app.services import distillation

router = APIRouter()


@router.get("/options")
def options(_user: str = Depends(get_current_user)) -> dict:
    return distillation.get_distillation_options()


class DistillationGenerateRequest(BaseModel):
    teacher_model: str = Field(..., alias="teacherModel")
    training_dataset: str = Field(..., alias="trainingDataset")
    instruction: str = ""

    model_config = {"populate_by_name": True}


class DistillationSamplePayload(BaseModel):
    id: int
    context: str = ""
    ai_prediction: str = Field("", alias="aiPrediction")
    verified_score: str = Field("", alias="verifiedScore")
    cot_trace: str = Field("", alias="cotTrace")

    model_config = {"populate_by_name": True}


class DistillationSaveRequest(BaseModel):
    teacher_model: str = Field(..., alias="teacherModel")
    training_dataset: str = Field(..., alias="trainingDataset")
    samples: list[DistillationSamplePayload]

    model_config = {"populate_by_name": True}


@router.post("/generate-dataset")
def generate_dataset(body: DistillationGenerateRequest, _user: str = Depends(get_current_user)) -> dict:
    return distillation.generate_distillation_dataset(
        body.teacher_model,
        body.training_dataset,
        body.instruction,
    )


@router.post("/generate-dataset/stream")
async def generate_dataset_stream(
    request: Request,
    body: DistillationGenerateRequest,
    _user: str = Depends(get_current_user),
) -> StreamingResponse:
    """SSE 流式返回 CoT 生成步骤与日志；客户端断开或中止时停止后台生成。"""
    cancel_event = distillation.request_cancel_event()

    async def event_stream():
        sync_gen = distillation.iter_sse_lines(
            body.teacher_model,
            body.training_dataset,
            body.instruction,
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


@router.post("/save-dataset")
def save_dataset(body: DistillationSaveRequest, _user: str = Depends(get_current_user)) -> dict:
    payload: list[dict[str, Any]] = [s.model_dump(by_alias=False) for s in body.samples]
    return distillation.save_distillation_finetune_dataset(
        body.teacher_model,
        body.training_dataset,
        payload,
    )


@router.post("/upload-training-dataset")
async def upload_training_dataset(
    file: UploadFile = File(...),
    _user: str = Depends(get_current_user),
) -> dict:
    raw = await file.read()
    try:
        return distillation.upload_training_dataset(file.filename or "dataset.csv", raw)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/training-dataset-template")
def training_dataset_template(_user: str = Depends(get_current_user)) -> Response:
    content = distillation.training_dataset_template_content()
    return Response(
        content=content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="distillation_template.csv"'},
    )


@router.get("/finetune-datasets")
def list_finetune_datasets(_user: str = Depends(get_current_user)) -> dict:
    return distillation.list_recent_finetune_records()
