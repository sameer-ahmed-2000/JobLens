import os
import json
import logging
from typing import List, Dict, Any, Optional
from app.models.schemas import RawPosting
from app.repositories.uow import UnitOfWork

logger = logging.getLogger(__name__)

def fetch_postings(file_path: Optional[str] = None) -> List[RawPosting]:
    """Load postings from PostgreSQL via JobRepository. Fallback to file_path if explicitly provided for evaluations."""
    if file_path is not None and os.path.exists(file_path):
        logger.info(f"Loading postings from explicit file: {file_path}")
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            postings = [RawPosting(**item) for item in data]
            return postings
        except Exception as e:
            logger.error(f"Failed to load postings from file {file_path}: {e}")

    logger.info("Fetching job postings from PostgreSQL via JobRepository...")
    try:
        with UnitOfWork() as uow:
            postings = uow.jobs.get_all_postings()
            if not postings:
                logger.info("Database empty on fetch; triggering automatic seed_if_empty()...")
                from app.services.seeder import seed_if_empty
                seed_if_empty()
                postings = uow.jobs.get_all_postings()
            logger.info(f"Successfully loaded {len(postings)} active job postings from database.")
            return postings
    except Exception as e:
        logger.error(f"Database query failed in fetch_postings: {e}")
        # Last resort fallback if database is not migrated or unavailable
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        fallback_path = os.path.join(base_dir, "data", "postings.json")
        if os.path.exists(fallback_path):
            with open(fallback_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return [RawPosting(**item) for item in data]
        raise e

def fetch_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """LangGraph node to fetch postings."""
    logger.info("Executing fetch_node...")
    postings = fetch_postings()
    return {"postings": postings}
