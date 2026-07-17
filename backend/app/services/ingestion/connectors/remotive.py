import time
import logging
from typing import Dict, Any
from app.services.ingestion.connectors.base import BaseConnector, ConnectorResultV1

logger = logging.getLogger(__name__)


class RemotiveConnector(BaseConnector):
    """
    Real-time keyword-driven connector for the Remotive remote-jobs API.
    No API key required. Supports a `search` querystring param that does a
    case-insensitive partial match against title + description.
    """

    def fetch(self, source_config: Dict[str, Any]) -> ConnectorResultV1:
        start_time = time.time()
        source_name = source_config.get("name", "Remotive:search")

        keywords = source_config.get("keywords") or []
        search_term = keywords[0] if keywords else ""

        url = "https://remotive.com/api/remote-jobs"
        params = {"search": search_term} if search_term else {}

        logger.info(f"RemotiveConnector: searching '{search_term}'...")
        data = self._http_get_with_retry(url, params=params)
        duration = time.time() - start_time

        if data and "jobs" in data:
            jobs = data["jobs"]
            logger.info(f"RemotiveConnector: fetched {len(jobs)} jobs in {duration:.2f}s")
            return ConnectorResultV1(
                source=source_name, duration=duration, jobs_fetched=len(jobs),
                failures=0, status="Success", raw_items=jobs
            )
        else:
            logger.warning("RemotiveConnector: failed to fetch jobs")
            return ConnectorResultV1(
                source=source_name, duration=duration, jobs_fetched=0,
                failures=1, status="Failed", raw_items=[]
            )
