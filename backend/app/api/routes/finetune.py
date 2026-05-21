from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.api.deps import get_current_user
from app.services import finetune_service
from app.services.finetune_generation import iter_sse_lines

router = APIRouter()


@router.get("/options")
def options(_user: str = Depends(get_current_user)) -> dict:
    return finetune_service.get_finetune_options()


class FineTuneRequest(BaseModel):
    base_model: str = Field(..., alias="baseModel")
    lora_rank: int = Field(64, alias="loraRank")
    lora_alpha: int = Field(128, alias="loraAlpha")
    lora_dropout: float = Field(0.05, alias="loraDropout")
    epoch: int = 3
    batch_size: int = Field(1, alias="batchSize")
    learning_rate: str = Field("2e-5", alias="learningRate")
    model_name: str = Field("", alias="modelName")

    model_config = {"populate_by_name": True}


class PublishRequest(BaseModel):
    model_name: str = Field(..., alias="modelName")
    checkpoint: str = ""
    base_model: str = Field("", alias="baseModel")

    model_config = {"populate_by_name": True}


@router.post("/run")
def run(body: FineTuneRequest, _user: str = Depends(get_current_user)) -> dict:
    return finetune_service.run_lora_finetune(body.model_dump(by_alias=True))


@router.post("/run/stream")
def run_stream(body: FineTuneRequest, _user: str = Depends(get_current_user)) -> StreamingResponse:
    payload = body.model_dump(by_alias=True)
    return StreamingResponse(
        iter_sse_lines(payload),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/publish")
def publish(body: PublishRequest, _user: str = Depends(get_current_user)) -> dict:
    if body.checkpoint and body.base_model:
        return finetune_service.publish_finetuned_model(
            body.model_name,
            checkpoint=body.checkpoint,
            base_model_registry_id=body.base_model,
        )
    return finetune_service.publish_model(body.model_name)
