from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from app.api.deps import get_current_user
from app.services import extraction_service, model_config_service

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
    text = extraction_service.decode_upload_bytes(raw, file.filename)
    try:
        return extraction_service.run_extraction(text, model, task_description)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


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
