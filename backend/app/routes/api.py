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
async def trigger_discovery(force_live_search: bool = False):
    """
    Triggers the discovery pipeline: first runs a resume-driven real-time
    search against aggregator sources (Adzuna/Remotive/Arbeitnow) using
    keywords derived from the active resume, then scores and ranks the
    combined pool (ATS boards + live aggregator results) via LangGraph.

    `force_live_search=true` bypasses the debounce window (useful for a
    manual "search now" button in the UI).
    """
    from app.services.resume_index import resume_index
    from app.services.job_scheduler import job_scheduler

    keywords = resume_index.get_search_keywords()
    if keywords:
        job_scheduler.trigger_live_search(keywords=keywords, force=force_live_search)

    return await discovery_service.get_ranked_postings()


@router.post("/gap-report", response_model=GapReport)
async def generate_gap_report(request: GapReportRequest):
    """
    Generates a gap report for a specific job description or URL using LangGraph.
    """
    return await gap_service.analyze_gap(request)


@router.get("/ingestion/status")
async def get_ingestion_status():
    """
    Returns diagnostic operational status of the latest ingestion runs and embedding queue size.
    """
    from app.repositories.uow import UnitOfWork
    from app.services.ingestion.queue import embedding_queue
    with UnitOfWork() as uow:
        latest_runs = uow.ingestion_runs.get_latest(limit=5)
    return {
        "runs": latest_runs,
        "queue_size": embedding_queue.size()
    }


@router.get("/scheduler/status")
async def get_scheduler_status():
    """
    Returns diagnostic status of the independent job scheduler and embedding worker queue.
    """
    from app.services.job_scheduler import job_scheduler
    from app.services.ingestion.queue import embedding_queue
    status_data = job_scheduler.get_status()
    status_data["queue_size"] = embedding_queue.size()
    return status_data


