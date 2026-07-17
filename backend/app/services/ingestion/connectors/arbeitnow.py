import time
import logging
from typing import Dict, Any
from app.services.ingestion.connectors.base import BaseConnector, ConnectorResultV1

logger = logging.getLogger(__name__)


class ArbeitnowConnector(BaseConnector):
    """
    Real-time connector for the Arbeitnow job board API (no auth required).
    Arbeitnow's public endpoint doesn't support a server-side `search` param,
    so this pulls the first couple of pages and relies on the pipeline's
    post-fetch keyword filter (run_ingestion_pipeline) to narrow results.
    """

    PAGES_TO_FETCH = 2

    def fetch(self, source_config: Dict[str, Any]) -> ConnectorResultV1:
        start_time = time.time()
        source_name = source_config.get("name", "Arbeitnow:search")

        base_url = "https://www.arbeitnow.com/api/job-board-api"
        all_jobs = []
        failures = 0

        for page in range(1, self.PAGES_TO_FETCH + 1):
            data = self._http_get_with_retry(base_url, params={"page": page})
            if data and "data" in data:
                all_jobs.extend(data["data"])
            else:
                failures += 1
                break  # stop paginating on first failure

        duration = time.time() - start_time

        if all_jobs:
            logger.info(f"ArbeitnowConnector: fetched {len(all_jobs)} jobs across {self.PAGES_TO_FETCH} pages in {duration:.2f}s")
            return ConnectorResultV1(
                source=source_name, duration=duration, jobs_fetched=len(all_jobs),
                failures=failures, status="Success" if failures == 0 else "Partial", raw_items=all_jobs
            )
        else:
            logger.warning("ArbeitnowConnector: failed to fetch jobs")
            return ConnectorResultV1(
                source=source_name, duration=duration, jobs_fetched=0,
                failures=1, status="Failed", raw_items=[]
            )
