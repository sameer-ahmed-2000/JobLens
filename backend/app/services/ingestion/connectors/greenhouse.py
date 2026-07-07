import time
import logging
from typing import Dict, Any
from app.services.ingestion.connectors.base import BaseConnector, ConnectorResultV1

logger = logging.getLogger(__name__)

class GreenhouseConnector(BaseConnector):
    def fetch(self, source_config: Dict[str, Any]) -> ConnectorResultV1:
        start_time = time.time()
        board = source_config.get("board") or source_config.get("url")
        source_name = source_config.get("name", f"Greenhouse:{board}")
        if not board:
            return ConnectorResultV1(
                source=source_name,
                duration=0.0,
                jobs_fetched=0,
                failures=1,
                status="Failed",
                raw_items=[]
            )

        url = f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs?content=true"
        logger.info(f"GreenhouseConnector: fetching jobs for board '{board}'...")
        data = self._http_get_with_retry(url)
        duration = time.time() - start_time

        if data and "jobs" in data:
            jobs = data["jobs"]
            logger.info(f"GreenhouseConnector: fetched {len(jobs)} jobs for '{board}' in {duration:.2f}s")
            return ConnectorResultV1(
                source=source_name,
                duration=duration,
                jobs_fetched=len(jobs),
                failures=0,
                status="Success",
                raw_items=jobs
            )
        else:
            logger.warning(f"GreenhouseConnector: failed to fetch jobs for '{board}'")
            return ConnectorResultV1(
                source=source_name,
                duration=duration,
                jobs_fetched=0,
                failures=1,
                status="Failed",
                raw_items=[]
            )
