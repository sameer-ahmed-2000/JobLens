"""
Career Workspace — Dashboard Metrics API
"""
import logging
from fastapi import APIRouter
from app.services.dashboard_service import dashboard_service

logger = logging.getLogger("dashboard_api")
router = APIRouter()

DEFAULT_USER_ID = "default-user-id"

@router.get("/dashboard")
def get_dashboard_metrics():
    """
    Returns aggregated metrics for the Career Workspace dashboard.
    """
    return dashboard_service.get_metrics(DEFAULT_USER_ID)
