import logging
from fastapi import APIRouter

logger = logging.getLogger(__name__)

router = APIRouter()


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


@router.get("/admin/dlq")
async def get_dlq():
    """
    Returns contents of the embedding Dead Letter Queue (DLQ).
    """
    from app.services.ingestion.queue import embedding_queue
    return embedding_queue.get_dlq_entries()
