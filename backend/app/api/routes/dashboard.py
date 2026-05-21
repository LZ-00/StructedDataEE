from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.services import dashboard_service

router = APIRouter()


@router.get("/stats")
def stats(_user: str = Depends(get_current_user)) -> dict:
    return dashboard_service.get_dashboard_stats()


@router.get("/stat-cards")
def stat_cards(_user: str = Depends(get_current_user)) -> list:
    return dashboard_service.get_stat_cards()


@router.get("/charts")
def charts(_user: str = Depends(get_current_user)) -> dict:
    return dashboard_service.get_dashboard_charts()
