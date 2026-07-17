import time
import threading
import logging
import json
from typing import Dict, Any, Optional
from app.repositories.uow import UnitOfWork
from app.services.similarity import cosine_similarity
from app.models.orm import ResumeORM, UserORM, JobORM

logger = logging.getLogger("scoring_service")

class ActiveResumesCache:
    def __init__(self, refresh_interval: float = 60.0):
        self.refresh_interval = refresh_interval
        self._cache: Dict[str, Dict[str, Any]] = {}  # user_id -> {"embedding": List[float], "display_threshold": float, "notify_threshold": float}
        self._lock = threading.Lock()
        self._timer: Optional[threading.Timer] = None
        self._running = False

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        # Populate immediately on startup
        try:
            self.refresh()
        except Exception as e:
            logger.error(f"Initial cache refresh failed: {e}", exc_info=True)
        self._refresh_loop()

    def stop(self) -> None:
        self._running = False
        if self._timer:
            self._timer.cancel()
            self._timer = None
        logger.info("ActiveResumesCache background refresh timer stopped.")

    def _refresh_loop(self) -> None:
        if not self._running:
            return
        try:
            self.refresh()
        except Exception as e:
            logger.error(f"Error in ActiveResumesCache refresh timer: {e}", exc_info=True)
        
        # Schedule next run if still running
        if self._running:
            self._timer = threading.Timer(self.refresh_interval, self._refresh_loop)
            self._timer.daemon = True
            self._timer.start()

    def refresh(self) -> None:
        logger.debug("Refreshing active resumes cache from DB...")
        new_cache = {}
        with UnitOfWork() as uow:
            results = uow.session.query(
                ResumeORM.user_id,
                ResumeORM.embedding,
                UserORM.display_threshold,
                UserORM.notify_threshold
            ).join(UserORM, ResumeORM.user_id == UserORM.id).filter(
                ResumeORM.is_active == True
            ).all()

            for user_id, embedding, display_threshold, notify_threshold in results:
                if embedding is not None:
                    # embedding could be a list (from VECTOR type result processor) or a serialized JSON string
                    if isinstance(embedding, str):
                        try:
                            emb_list = json.loads(embedding)
                        except Exception:
                            logger.error(f"Failed to parse embedding JSON for user {user_id}")
                            continue
                    else:
                        emb_list = list(embedding)
                    
                    new_cache[user_id] = {
                        "embedding": emb_list,
                        "display_threshold": display_threshold,
                        "notify_threshold": notify_threshold
                    }

        # Atomically swap reference under lock to prevent race conditions during updates
        with self._lock:
            self._cache = new_cache
        logger.info(f"Refreshed active resumes cache. Loaded {len(new_cache)} active resumes.")

    def get_all(self) -> Dict[str, Dict[str, Any]]:
        with self._lock:
            return dict(self._cache)


class ScoringService:
    def __init__(self, refresh_interval: float = 60.0):
        self.cache = ActiveResumesCache(refresh_interval=refresh_interval)

    def start(self) -> None:
        self.cache.start()

    def stop(self) -> None:
        self.cache.stop()

    def score_job_for_all_users(self, job_id: str, publish_events: bool = True) -> None:
        """
        Loads the job embedding from the DB, computes similarity against all cached
        active user resumes, upserts the results in job_matches, and optionally
        publishes match events above threshold to user-specific Redis channels.
        """
        with UnitOfWork() as uow:
            job = uow.session.query(JobORM).filter(JobORM.id == job_id).first()
            if not job:
                logger.warning(f"ScoringService: Job '{job_id}' not found in database.")
                return

            job_embedding = job.embedding
            if not job_embedding:
                logger.warning(f"ScoringService: Job '{job_id}' ({job.title}) has no embedding.")
                return

            if isinstance(job_embedding, str):
                try:
                    job_embedding = json.loads(job_embedding)
                except Exception as e:
                    logger.error(f"Failed to parse job embedding JSON for job '{job_id}': {e}")
                    return

            active_resumes = self.cache.get_all()
            if not active_resumes:
                logger.warning("ScoringService: Active resumes cache is empty. No jobs scored.")
                return

            for user_id, user_data in active_resumes.items():
                resume_embedding = user_data["embedding"]
                display_threshold = user_data["display_threshold"]

                sim = cosine_similarity(job_embedding, resume_embedding)
                score = round(sim, 4)

                # Upsert match record in DB (using UnitOfWork's repository)
                match_res = uow.job_matches.upsert(user_id=user_id, job_id=job_id, score=score)

                if publish_events and score >= display_threshold:
                    job_match_id = match_res["id"]
                    comp_name = job.company.name if job.company else "Unknown Company"
                    self._publish_match_event(
                        user_id=user_id,
                        job_match_id=job_match_id,
                        title=job.title,
                        company=comp_name,
                        score=score,
                        url=job.url,
                        source=job.source or "Live"
                    )

            uow.commit()
            logger.info(f"ScoringService: Completed scoring for job '{job.title}' ({job_id}) against {len(active_resumes)} users.")

    def _publish_match_event(
        self,
        user_id: str,
        job_match_id: str,
        title: str,
        company: str,
        score: float,
        url: str,
        source: str
    ) -> None:
        """Publishes the job match event to the user's specific Redis PubSub channel."""
        event_data = {
            "type": "new_match",
            "job_match_id": job_match_id,
            "title": title,
            "company": company,
            "score": score,
            "url": url,
            "source": source
        }
        channel_name = f"job_events:{user_id}"
        logger.info(f"Publishing match event for user {user_id} on {channel_name} (Score: {score:.4f})")

        from app.services.ingestion.queue import embedding_queue
        if hasattr(embedding_queue, "queue_backend") and embedding_queue.queue_backend == "redis":
            try:
                embedding_queue.client.publish(channel_name, json.dumps(event_data))
                logger.debug(f"Successfully published event to Redis channel {channel_name}.")
            except Exception as e:
                logger.error(f"Failed to publish event to Redis channel {channel_name}: {e}")
        else:
            logger.debug(f"Redis is not active. Skipped publishing event to channel {channel_name}.")

# Global singleton service
scoring_service = ScoringService()
