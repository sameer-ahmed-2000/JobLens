import time
import logging
from typing import Dict, Any
from app.services.ingestion.connectors.base import BaseConnector, ConnectorResultV1
from app.config import settings

logger = logging.getLogger(__name__)


class AdzunaConnector(BaseConnector):
    """
    Real-time keyword-driven connector for the Adzuna job search API.
    Unlike the ATS connectors (Greenhouse/Lever/Ashby), this queries by
    `what` (keywords) and `where` (location) directly, so it's the connector
    that actually powers resume-driven search rather than a fixed company board.

    Requires ADZUNA_APP_ID / ADZUNA_APP_KEY (free tier: https://developer.adzuna.com).
    """

    def fetch(self, source_config: Dict[str, Any]) -> ConnectorResultV1:
        start_time = time.time()
        source_name = source_config.get("name", "Adzuna:search")

        app_id = settings.adzuna_app_id
        app_key = settings.adzuna_app_key
        if not app_id or not app_key:
            logger.warning("AdzunaConnector: ADZUNA_APP_ID/ADZUNA_APP_KEY not configured. Skipping.")
            return ConnectorResultV1(
                source=source_name, duration=0.0, jobs_fetched=0,
                failures=1, status="Failed", raw_items=[]
            )

        keywords = source_config.get("keywords") or []
        location = source_config.get("location") or settings.default_location
        country = settings.adzuna_country

        what = " ".join(keywords[:5]) if keywords else ""
        url = f"https://api.adzuna.com/v1/api/jobs/{country}/search/1"
        params = {
            "app_id": app_id,
            "app_key": app_key,
            "results_per_page": 30,
            "content-type": "application/json",
        }
        if what:
            params["what"] = what
        if location:
            params["where"] = location

        logger.info(f"AdzunaConnector: searching '{what}' in '{location}' (country={country})...")
        data = self._http_get_with_retry(url, params=params)
        duration = time.time() - start_time

        if data and "results" in data:
            jobs = data["results"]
            logger.info(f"AdzunaConnector: fetched {len(jobs)} jobs in {duration:.2f}s")
            return ConnectorResultV1(
                source=source_name, duration=duration, jobs_fetched=len(jobs),
                failures=0, status="Success", raw_items=jobs
            )
        else:
            logger.warning("AdzunaConnector: failed to fetch jobs (check API credentials/quota)")
            return ConnectorResultV1(
                source=source_name, duration=duration, jobs_fetched=0,
                failures=1, status="Failed", raw_items=[]
            )
