import time
import logging
import threading
from typing import Optional, List, Dict, Any
from datetime import datetime
from app.config import settings
from app.services.ingestion.pipeline import run_ingestion_pipeline

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

    def trigger_now(self, keywords: Optional[List[str]] = None, location: Optional[str] = None) -> Dict[str, Any]:
        """Manually trigger ingestion pipeline execution."""
        logger.info("Manually triggering live job ingestion pipeline...")
        self.last_run = datetime.utcnow()
        stats = run_ingestion_pipeline(keywords=keywords, location=location)
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
            elapsed_minutes = (datetime.utcnow() - self.last_live_search).total_seconds() / 60.0
            if elapsed_minutes < min_interval:
                logger.info(
                    f"Skipping live search: last run {elapsed_minutes:.1f} min ago "
                    f"(min interval {min_interval} min)."
                )
                return {"status": "skipped_debounce", "minutes_since_last": round(elapsed_minutes, 1)}

        logger.info(f"Triggering resume-driven live search with keywords={keywords}, location={location}...")
        self.last_live_search = datetime.utcnow()
        stats = run_ingestion_pipeline(keywords=keywords, location=location)
        self.last_stats = stats
        return stats

    def _run_loop(self, run_immediately: bool) -> None:
        if run_immediately:
            try:
                self.trigger_now()
            except Exception as e:
                logger.error(f"Error during initial scheduler ingestion run: {e}", exc_info=True)

        while self._running:
            # Sleep in 1-second chunks so we can stop cleanly
            interval_seconds = self.interval_minutes * 60
            for _ in range(interval_seconds):
                if not self._running:
                    break
                time.sleep(1.0)
            
            if self._running:
                try:
                    self.trigger_now()
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
