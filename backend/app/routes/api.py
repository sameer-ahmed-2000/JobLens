from fastapi import APIRouter
from typing import List
import json
import os
from app.models.schemas import ScoredPosting, GapReportRequest, GapReport, RawPosting

router = APIRouter()

# Load mock data for phase 1
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")

from app.services.discovery_service import discovery_service
from app.services.gap_service import gap_service

@router.get("/postings", response_model=List[ScoredPosting])
async def get_postings():
    """
    Returns a list of job postings, scored and ranked against the user's resume using LangGraph.
    """
    return await discovery_service.get_ranked_postings()

@router.post("/discover", response_model=List[ScoredPosting])
async def trigger_discovery():
    """
    Triggers the discovery pipeline (LangGraph) to find, score, and rank jobs.
    """
    return await discovery_service.get_ranked_postings()


@router.post("/gap-report", response_model=GapReport)
async def generate_gap_report(request: GapReportRequest):
    """
    Generates a gap report for a specific job description or URL using LangGraph.
    """
    return await gap_service.analyze_gap(request)

