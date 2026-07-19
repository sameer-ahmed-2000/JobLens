import time
import logging
from typing import Dict, Any
from app.services.ingestion.connectors.base import BaseConnector, ConnectorResultV1
from app.config import settings

logger = logging.getLogger(__name__)


class JoobleConnector(BaseConnector):
    """
    Real-time keyword-driven connector for the Jooble job search API.
    Like AdzunaConnector, this queries by keywords + location directly rather
    than pulling a fixed company board -- it's a second independent aggregator
    layer (Jooble itself re-aggregates LinkedIn, Indeed, ZipRecruiter, and
    thousands of other boards), so it's not a duplicate of Adzuna's coverage.

    Requires JOOBLE_API_KEY (free, no card required: https://jooble.org/api/about).
    Unlike the other connectors, Jooble's search endpoint is POST with a JSON
    body rather than GET query params.
    """

    def fetch(self, source_config: Dict[str, Any]) -> ConnectorResultV1:
        start_time = time.time()
        source_name = source_config.get("name", "Jooble:search")

        api_key = settings.jooble_api_key
        if not api_key:
            logger.warning("JoobleConnector: JOOBLE_API_KEY not configured. Skipping.")
            return ConnectorResultV1(
                source=source_name, duration=0.0, jobs_fetched=0,
                failures=1, status="Failed", raw_items=[]
            )

        keywords = source_config.get("keywords") or []
        location = source_config.get("location") or settings.default_location

        url = f"https://jooble.org/api/{api_key}"
        body = {}
        if keywords:
            body["keywords"] = " ".join(keywords[:5])
        if location:
            body["location"] = location

        logger.info(f"JoobleConnector: searching '{body.get('keywords', '')}' in '{location}'...")
        data = self._http_post_with_retry(url, json_body=body)
        duration = time.time() - start_time

        if data and "jobs" in data:
            jobs = data["jobs"]
            logger.info(f"JoobleConnector: fetched {len(jobs)} jobs in {duration:.2f}s")
            return ConnectorResultV1(
                source=source_name, duration=duration, jobs_fetched=len(jobs),
                failures=0, status="Success", raw_items=jobs
            )
        else:
            logger.warning("JoobleConnector: failed to fetch jobs (check API key/quota)")
            return ConnectorResultV1(
                source=source_name, duration=duration, jobs_fetched=0,
                failures=1, status="Failed", raw_items=[]
            )
