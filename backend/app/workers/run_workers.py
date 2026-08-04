"""
Standalone worker process for JobLens background tasks.
Executes EmbeddingWorker, ScoringWorker, and JobScheduler independently
from the FastAPI web application process.

Deploy as a separate Docker service or Kubernetes deployment:
    python -m app.workers.run_workers
"""
import sys
import os
import time
import signal
import logging

# Ensure backend root directory is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.log_context import CorrelationIdFilter
from app.services.ingestion.embedding_worker import embedding_worker
from app.services.ingestion.scoring_worker import scoring_worker
from app.services.job_scheduler import job_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s [cid=%(correlation_id)s] - %(message)s"
)
logging.getLogger().addFilter(CorrelationIdFilter())
logger = logging.getLogger("run_workers")

def main():
    logger.info("=== Starting JobLens Standalone Background Worker Process ===")
    
    embedding_worker.start()
    scoring_worker.start()
    job_scheduler.start(run_immediately=True)
    
    running = True

    def shutdown_handler(signum, frame):
        nonlocal running
        logger.info("Shutdown signal received in worker process. Stopping background workers...")
        running = False

    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)

    try:
        while running:
            time.sleep(1.0)
    finally:
        logger.info("Stopping JobScheduler...")
        job_scheduler.stop()
        logger.info("Stopping ScoringWorker...")
        scoring_worker.stop()
        logger.info("Stopping EmbeddingWorker...")
        embedding_worker.stop()
        logger.info("=== Standalone Background Worker Process Stopped Cleanly ===")

if __name__ == "__main__":
    main()
