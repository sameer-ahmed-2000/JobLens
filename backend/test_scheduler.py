import os
import sys
import logging
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s - %(message)s")
logger = logging.getLogger("test_scheduler")

from app.services.job_scheduler import JobScheduler

def test_job_scheduler():
    logger.info("=== Starting Test: Independent JobScheduler Service ===")
    scheduler = JobScheduler(interval_minutes=30)
    
    with patch("app.services.job_scheduler.run_ingestion_pipeline") as mock_run:
        mock_run.return_value = {"status": "completed", "total_fetched": 15, "total_inserted": 2}
        
        stats = scheduler.trigger_now(keywords=["AI"], location="Remote")
        assert stats["total_fetched"] == 15
        assert mock_run.called
        
        status = scheduler.get_status()
        assert status["status"] == "stopped"
        assert status["interval_minutes"] == 30
        assert status["last_stats"]["total_inserted"] == 2
        assert status["last_run"] is not None

    logger.info("=== Test Passed: JobScheduler cleanly manages execution and diagnostic status! ===\n")

if __name__ == "__main__":
    try:
        test_job_scheduler()
        logger.info("=== JOB SCHEDULER TEST PASSED SUCCESSFULLY! ===")
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        sys.exit(1)
