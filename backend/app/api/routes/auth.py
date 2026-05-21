from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.core.security import create_access_token
from app.services.auth_service import verify_credentials

router = APIRouter()


class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/login")
def login(body: LoginRequest) -> dict:
    if verify_credentials(body.username.strip(), body.password):
        token = create_access_token(body.username.strip())
        return {"access_token": token, "token_type": "bearer"}
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误")
