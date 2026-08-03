"""
job_scheduler.py — JobScheduler service and optional standalone entry point.

DEPLOYMENT NOTE — embedded vs. standalone:

  The FastAPI app (main.py) automatically starts embedding_worker,
  scoring_worker, and job_scheduler on its startup event. This is the
  default deployment mode when you run `uvicorn app.main:app`.

  The __main__ block at the bottom of this file is a STANDALONE alternative
  intended for environments where the scheduler runs as a separate process
  (e.g. a separate container, worker dyno, or local debug session).

  Do NOT run both modes simultaneously against the same Redis unless you
  intentionally want multiple consumers on the embedding/scoring streams.
  Consumer groups will distribute messages (not duplicate them), so work
  won't be processed twice, but resource usage doubles and correlating logs
  across two independent process trees becomes harder. If in doubt, use
  only the embedded mode (FastAPI startup).
"""
import time
import logging
import threading
from typing import Optional, List, Dict, Any, Set
from datetime import datetime, timezone
from app.config import settings
from app.services.ingestion.pipeline import run_ingestion_pipeline, AGGREGATOR_TYPES, FIXED_BOARD_TYPES

logger = logging.getLogger("job_scheduler")

class JobScheduler:
    def __init__(self, interval_minutes: Optional[int] = None):
        self.interval_minutes = interval_minutes or getattr(settings, "ingestion_interval_minutes", 60)
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self.last_run: Optional[datetime] = None
        self.last_stats: Dict[str, Any] = {}
        self.last_live_search: Optional[datetime] = None

    def start(self, run_immediately: bool = True) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, args=(run_immediately,), daemon=True, name="JobSchedulerThread")
        self._thread.start()
        logger.info(f"JobScheduler started with {self.interval_minutes}-minute interval.")

    def stop(self) -> None:
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3.0)
        logger.info("JobScheduler stopped.")

    def trigger_now(
        self,
        keywords: Optional[List[str]] = None,
        location: Optional[str] = None,
        force: bool = False,
        source_types: Optional[frozenset] = None,
    ) -> Dict[str, Any]:
        """Manually trigger ingestion pipeline execution."""
        logger.info("Triggering live job ingestion pipeline (evaluating per-source poll intervals)...")
        self.last_run = datetime.now(timezone.utc)
        stats = run_ingestion_pipeline(keywords=keywords, location=location, force=force, source_types=source_types)
        self.last_stats = stats
        return stats

    def trigger_live_search(self, keywords: List[str], location: Optional[str] = None, force: bool = False) -> Dict[str, Any]:
        """
        Resume-driven real-time search against aggregator sources (Adzuna/Remotive/Arbeitnow).
        Debounced by `live_search_min_interval_minutes` so a burst of /discover
        calls doesn't hammer free-tier external APIs; pass force=True to bypass.
        """
        min_interval = getattr(settings, "live_search_min_interval_minutes", 15)
        if not force and self.last_live_search is not None:
            elapsed_minutes = (datetime.now(timezone.utc) - self.last_live_search).total_seconds() / 60.0
            if elapsed_minutes < min_interval:
                logger.info(
                    f"Skipping live search: last run {elapsed_minutes:.1f} min ago "
                    f"(min interval {min_interval} min)."
                )
                return {"status": "skipped_debounce", "minutes_since_last": round(elapsed_minutes, 1)}

        logger.info(f"Triggering resume-driven live search with keywords={keywords}, location={location}...")
        self.last_live_search = datetime.now(timezone.utc)
        stats = run_ingestion_pipeline(keywords=keywords, location=location, force=force)
        self.last_stats = stats
        return stats

    def _run_user_keyword_rotation(self) -> None:
        """
        Picks a small batch of the least-recently-searched active users and runs
        a keyword-scoped aggregator search on their behalf, so the shared job pool
        stays enriched with resume-relevant postings continuously — not just when
        someone manually clicks Refresh.

        Rotates rather than covering every user every tick to stay within
        aggregator free-tier rate limits. Batch size is controlled via
        JOBS_PER_USER_ROTATION_BATCH_SIZE (default 3).

        Per-user failures are isolated so one user's bad resume/keyword data
        doesn't block the rest of the rotation batch — same principle already
        applied in scoring_service.py.
        """
        from app.repositories.uow import UnitOfWork
        from app.services.resume_index import resume_index

        batch_size = getattr(settings, "jobs_per_user_rotation_batch_size", 3)

        try:
            with UnitOfWork() as uow:
                users = uow.users.get_users_for_rotation(limit=batch_size)
        except Exception as e:
            logger.error(f"Could not load users for keyword rotation: {e}", exc_info=True)
            return

        if not users:
            logger.debug("Keyword rotation: no users found.")
            return

        logger.info(f"Keyword rotation tick: processing {len(users)} user(s)...")
        for user in users:
            try:
                keywords = resume_index.get_search_keywords(user_id=user["id"])
                if not keywords:
                    logger.info(f"Rotation: skipping user {user['id']} — no resume keywords available.")
                    # Still stamp the timestamp so this user doesn't stay at the
                    # head of the queue indefinitely blocking users with resumes.
                    with UnitOfWork() as uow:
                        uow.users.update_last_keyword_search(user["id"])
                        uow.commit()
                    continue

                logger.info(
                    f"Rotation: running aggregator search for user {user['id']} "
                    f"with keywords={keywords}..."
                )
                run_ingestion_pipeline(
                    keywords=keywords,
                    location=getattr(settings, "default_location", None) or None,
                    source_types=AGGREGATOR_TYPES,
                )

                with UnitOfWork() as uow:
                    uow.users.update_last_keyword_search(user["id"])
                    uow.commit()

            except Exception as e:
                logger.error(
                    f"Rotation failed for user {user['id']}: {e}", exc_info=True
                )

    def _run_loop(self, run_immediately: bool) -> None:
        if run_immediately:
            try:
                # On first boot: run everything broadly (no source_types filter)
                # so the shared job pool gets a full initial population before
                # the rotation kicks in on the first regular tick.
                self.trigger_now(force=True)
            except Exception as e:
                logger.error(f"Error during initial scheduler ingestion run: {e}", exc_info=True)

        while self._running:
            # Ticks every 60s; per-source poll_interval_minutes in pipeline.py
            # decides which sources actually fetch on any given tick.
            for _ in range(60):
                if not self._running:
                    break
                time.sleep(1.0)

            if self._running:
                try:
                    # Scope regular ticks to fixed-board sources only (no keywords
                    # needed) so aggregators aren't wasted on unscoped generic feeds.
                    self.trigger_now(force=False, source_types=FIXED_BOARD_TYPES)
                    # Resume-driven aggregator search, rotating across users each tick.
                    self._run_user_keyword_rotation()
                except Exception as e:
                    logger.error(f"Error during scheduled ingestion run: {e}", exc_info=True)


    def get_status(self) -> Dict[str, Any]:
        return {
            "status": "running" if self._running else "stopped",
            "interval_minutes": self.interval_minutes,
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "last_live_search": self.last_live_search.isoformat() if self.last_live_search else None,
            "last_stats": self.last_stats
        }

# Global singleton scheduler instance
job_scheduler = JobScheduler()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s - %(message)s")
    logger.info("Starting standalone JobScheduler process...")
    from app.services.ingestion.embedding_worker import embedding_worker
    from app.services.ingestion.scoring_worker import scoring_worker
    from app.notifier import Notifier
    import threading

    embedding_worker.start()
    scoring_worker.start()
    
    # Start the Notifier Subscriber in a background thread
    notifier_instance = Notifier()
    notifier_thread = threading.Thread(target=notifier_instance.start, daemon=True, name="NotifierProcessThread")
    notifier_thread.start()

    job_scheduler.start(run_immediately=True)
    try:
        while True:
            time.sleep(5.0)
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received. Shutting down standalone scheduler...")
        job_scheduler.stop()
        scoring_worker.stop()
        embedding_worker.stop()
        notifier_instance.stop()
