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
            "last_stats": self.last_stats
        }

# Global singleton scheduler instance
job_scheduler = JobScheduler()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s - %(message)s")
    logger.info("Starting standalone JobScheduler process...")
    from app.services.ingestion.embedding_worker import embedding_worker
    embedding_worker.start()
    job_scheduler.start(run_immediately=True)
    try:
        while True:
            time.sleep(5.0)
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received. Shutting down standalone scheduler...")
        job_scheduler.stop()
        embedding_worker.stop()
