import time
import logging
from typing import List
from fastapi import HTTPException
from app.models.schemas import ScoredPosting
from app.graphs.discovery_graph import discovery_graph
from app.config import settings
from app.repositories.uow import UnitOfWork

logger = logging.getLogger("discovery_service")

class DiscoveryService:
    async def get_ranked_postings(self, user_id: str = "default-user-id", force_refresh: bool = False) -> List[ScoredPosting]:
        """
        Execute the LangGraph Discovery workflow and return ranked job postings.
        Utilizes JobMatchRepository cache if force_refresh=False.
        """
        logger.info(f"Discovery started for user: {user_id} (force_refresh={force_refresh})")
        t0 = time.perf_counter()

        # 1. Try reading from JobMatchRepository cache if not forcing refresh
        if not force_refresh:
            try:
                with UnitOfWork() as uow:
                    existing_matches = uow.job_matches.get_matches_for_user(user_id)
                if existing_matches:
                    logger.info(f"Found {len(existing_matches)} cached job matches for user {user_id}")
                    return [ScoredPosting(**m) for m in existing_matches]
            except Exception as e:
                logger.warning(f"Error checking cached matches: {e}; proceeding to live discovery.")

        # 2. Run LangGraph discovery pipeline
        try:
            state = discovery_graph.invoke({"user_id": user_id})
        except FileNotFoundError as e:
            logger.error(f"Discovery pipeline failed (File not found): {e}")
            raise HTTPException(status_code=404, detail=f"Data file missing: {str(e)}")
        except ValueError as e:
            logger.error(f"Discovery pipeline failed (Validation/JSON error): {e}")
            raise HTTPException(status_code=400, detail=f"Data error: {str(e)}")
        except Exception as e:
            logger.error(f"Discovery pipeline failed unexpectedly: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Internal error during discovery pipeline execution.")
        
        scored = state.get("scored_postings", [])
        
        # 3. Save/upsert scored matches in database
        try:
            with UnitOfWork() as uow:
                uow.job_matches.upsert_matches(user_id, scored)
                uow.commit()
                logger.info(f"Saved {len(scored)} scored matches to DB for user {user_id}")
        except Exception as e:
            logger.error(f"Failed to cache job matches in database: {e}", exc_info=True)

        # 4. Query them back from the DB to ensure we get definitive ordering and database-driven statuses
        try:
            with UnitOfWork() as uow:
                matches = uow.job_matches.get_matches_for_user(user_id)
            elapsed = time.perf_counter() - t0
            logger.info(f"Discovery completed for user {user_id} in {elapsed:.2f} s")
            return [ScoredPosting(**m) for m in matches]
        except Exception as e:
            logger.error(f"Failed to fetch matches back from DB: {e}. Returning in-memory results.", exc_info=True)
            return scored

# Singleton instance
discovery_service = DiscoveryService()
