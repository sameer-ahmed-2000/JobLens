"""
Career Workspace — Dashboard Metrics API
"""
import logging
from fastapi import APIRouter, Depends
from app.services.dashboard_service import dashboard_service
from app.routes.auth import get_current_user_id

logger = logging.getLogger("dashboard_api")
router = APIRouter()

@router.get("/dashboard")
def get_dashboard_metrics(current_user_id: str = Depends(get_current_user_id)):
    """
    Returns aggregated metrics for the Career Workspace dashboard.
    """
    return dashboard_service.get_metrics(current_user_id)
