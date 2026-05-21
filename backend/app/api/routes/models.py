from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from app.api.deps import get_current_user
from app.config import model_catalog as catalog
from app.services import model_config_service

router = APIRouter()


@router.get("/options")
def options(_user: str = Depends(get_current_user)) -> dict:
    return model_config_service.get_form_options()


@router.get("")
def list_models(
    include_disabled: bool = False,
    _user: str = Depends(get_current_user),
) -> dict:
    return {"models": model_config_service.list_models(include_disabled=include_disabled)}


@router.get("/{model_id}")
def get_model(model_id: str, _user: str = Depends(get_current_user)) -> dict:
    item = model_config_service.get_model(model_id)
    if not item:
        raise HTTPException(status_code=404, detail="模型不存在")
    return item


class ApiConfigBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    base_url: str = Field("", alias="baseUrl")
    api_key: str = Field("", alias="apiKey")
    model_id: str = Field(..., alias="modelId")
    temperature: float = 0.7
    max_tokens: int = Field(4096, alias="maxTokens")


class LocalConfigBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    model_id: str = Field(..., alias="modelId")
    base_dir: str = Field(catalog.DEFAULT_LOCAL_BASE_DIR, alias="baseDir")
    local_path: str = Field("", alias="localPath")


class UpdateLocalConfigBody(BaseModel):
    """编辑时允许部分字段更新。"""

    model_config = ConfigDict(populate_by_name=True)

    model_id: Optional[str] = Field(None, alias="modelId")
    base_dir: Optional[str] = Field(None, alias="baseDir")
    local_path: Optional[str] = Field(None, alias="localPath")


class UpdateApiConfigBody(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    base_url: Optional[str] = Field(None, alias="baseUrl")
    api_key: Optional[str] = Field(None, alias="apiKey")
    model_id: Optional[str] = Field(None, alias="modelId")
    temperature: Optional[float] = None
    max_tokens: Optional[int] = Field(None, alias="maxTokens")


class CreateModelRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str
    type: str
    description: str = ""
    enabled: bool = True
    api_config: Optional[ApiConfigBody] = Field(None, alias="apiConfig")
    local_config: Optional[LocalConfigBody] = Field(None, alias="localConfig")


class UpdateModelRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: Optional[str] = None
    description: Optional[str] = None
    enabled: Optional[bool] = None
    api_config: Optional[UpdateApiConfigBody] = Field(None, alias="apiConfig")
    local_config: Optional[UpdateLocalConfigBody] = Field(None, alias="localConfig")


class DownloadModelRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    model_id: str = Field(..., alias="modelId")
    base_dir: str = Field(catalog.DEFAULT_LOCAL_BASE_DIR, alias="baseDir")


@router.post("")
def create_model(body: CreateModelRequest, _user: str = Depends(get_current_user)) -> dict:
    payload = body.model_dump(by_alias=True)
    if body.api_config:
        payload["api_config"] = body.api_config.model_dump(by_alias=True)
    if body.local_config:
        payload["local_config"] = body.local_config.model_dump(by_alias=True)
    try:
        return model_config_service.create_model(payload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except OSError as e:
        raise HTTPException(status_code=500, detail=f"无法写入模型注册表: {e}") from e


@router.put("/{model_id}")
def update_model(
    model_id: str,
    body: UpdateModelRequest,
    _user: str = Depends(get_current_user),
) -> dict:
    payload = body.model_dump(by_alias=True, exclude_none=True)
    if body.api_config:
        payload["api_config"] = body.api_config.model_dump(by_alias=True)
    if body.local_config:
        payload["local_config"] = body.local_config.model_dump(by_alias=True)
    try:
        return model_config_service.update_model(model_id, payload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except OSError as e:
        raise HTTPException(status_code=500, detail=f"无法写入模型注册表: {e}") from e


@router.delete("/{model_id}")
def delete_model(model_id: str, _user: str = Depends(get_current_user)) -> dict:
    try:
        model_config_service.delete_model(model_id)
        return {"success": True}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.post("/{model_id}/test")
def test_model(model_id: str, _user: str = Depends(get_current_user)) -> dict:
    try:
        return model_config_service.test_model_connection(model_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.post("/download")
def download_model(body: DownloadModelRequest, _user: str = Depends(get_current_user)) -> dict:
    try:
        return model_config_service.download_local_model(body.model_id, body.base_dir)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
