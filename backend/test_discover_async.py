import os
import sys
import time
import logging
from unittest.mock import patch, MagicMock

# Ensure backend directory is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("test_discover_async")

def test_async_discovery():
    logger.info("=== Starting Test: Async Discovery (/api/discover) ===")
    
    # Mock startup workers/scheduler to avoid hitting external APIs during TestClient creation
    with patch("app.services.ingestion.embedding_worker.embedding_worker.start") as mock_embed_start, \
         patch("app.services.ingestion.scoring_worker.scoring_worker.start") as mock_score_start, \
         patch("app.services.job_scheduler.job_scheduler.start") as mock_sched_start:
         
        from app.main import app
        client = TestClient(app)
        
        headers = {"Authorization": "Bearer default-user-token"}

        # Mock get_search_keywords to return a dummy keyword list
        # and mock get_ranked_postings to return an empty list immediately
        with patch("app.services.resume_index.resume_index.get_search_keywords", return_value=["Python"]), \
             patch("app.services.discovery_service.discovery_service.get_ranked_postings", return_value=[]) as mock_get_ranked, \
             patch("app.services.job_scheduler.job_scheduler.trigger_live_search") as mock_trigger_live, \
             patch("app.services.scoring_service.scoring_service.cache.refresh") as mock_cache_refresh:

            # Time the HTTP request execution
            start_time = time.perf_counter()
            resp = client.post("/api/discover", headers=headers, params={"force_live_search": True})
            elapsed = time.perf_counter() - start_time

            logger.info(f"Request finished in {elapsed*1000:.2f} ms")

            # 1. Assert successful response
            assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
            
            # 2. Verify cached/existing ranked postings were fetched without force_refresh
            mock_get_ranked.assert_called_once_with(user_id="default-user-id", force_refresh=False)

            # 3. Verify active resume cache was refreshed synchronously
            mock_cache_refresh.assert_called_once()

            # 4. Verify live search was triggered (FastAPI's TestClient runs background tasks synchronously by default)
            mock_trigger_live.assert_called_once_with(keywords=["Python"], force=True)

            logger.info("Passed: live search was queued and run, and the request returned cached postings immediately!")

if __name__ == "__main__":
    try:
        test_async_discovery()
        logger.info("=== ASYNC DISCOVERY TEST PASSED SUCCESSFULLY! ===")
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        sys.exit(1)
