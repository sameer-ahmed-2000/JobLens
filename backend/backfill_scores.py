import os
import sys
import logging

# Ensure backend directory is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s - %(message)s")
logger = logging.getLogger("backfill_scores")

from app.repositories.uow import UnitOfWork
from app.models.orm import JobORM, JobMatchORM
from app.services.scoring_service import scoring_service

def run_backfill():
    logger.info("=== Starting Job Match Score Backfill ===")
    
    # 1. Refresh cache synchronously
    try:
        scoring_service.cache.refresh()
    except Exception as e:
        logger.error(f"Failed to refresh active resumes cache: {e}")
        sys.exit(1)

    active_users = list(scoring_service.cache.get_all().keys())
    if not active_users:
        logger.warning("No active users with active resumes found. Nothing to backfill.")
        return

    logger.info(f"Found active users: {active_users}")

    # 2. Query all job IDs that have embeddings
    with UnitOfWork() as uow:
        embedded_jobs = uow.session.query(JobORM.id, JobORM.title).filter(JobORM.embedding != None).all()
        
    logger.info(f"Found {len(embedded_jobs)} jobs with embeddings in database.")
    
    scored_count = 0
    for job_id, title in embedded_jobs:
        # Check if this job has already been scored for all active users to avoid redundant work
        with UnitOfWork() as uow:
            existing_match_users = uow.session.query(JobMatchORM.user_id).filter(
                JobMatchORM.job_id == job_id,
                JobMatchORM.user_id.in_(active_users)
            ).all()
            existing_match_users = {r[0] for r in existing_match_users}

        missing_users = set(active_users) - existing_match_users
        if not missing_users:
            logger.debug(f"Job '{title}' ({job_id}) already scored for all active users. Skipping.")
            continue

        logger.info(f"Scoring job '{title}' ({job_id}) for missing users: {missing_users}")
        try:
            # Score this job for all users with events disabled
            scoring_service.score_job_for_all_users(job_id, publish_events=False)
            scored_count += 1
        except Exception as e:
            logger.error(f"Failed to score job '{job_id}': {e}")

    logger.info(f"=== Backfill Completed. Scored {scored_count} new job-user pairs. ===")

if __name__ == "__main__":
    run_backfill()
