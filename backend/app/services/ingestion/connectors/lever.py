import time
import logging
from typing import Dict, Any, List
from app.services.ingestion.connectors.base import BaseConnector, ConnectorResultV1

logger = logging.getLogger(__name__)

class LeverConnector(BaseConnector):
    def fetch(self, source_config: Dict[str, Any]) -> ConnectorResultV1:
        start_time = time.time()
        board = source_config.get("board") or source_config.get("url")
        source_name = source_config.get("name", f"Lever:{board}")
        if not board:
            return ConnectorResultV1(
                source=source_name,
                duration=0.0,
                jobs_fetched=0,
                failures=1,
                status="Failed",
                raw_items=[]
            )

        url = f"https://api.lever.co/v0/postings/{board}?mode=json"
        logger.info(f"LeverConnector: fetching jobs for board '{board}'...")
        data = self._http_get_with_retry(url)
        duration = time.time() - start_time

        if isinstance(data, list):
            logger.info(f"LeverConnector: fetched {len(data)} jobs for '{board}' in {duration:.2f}s")
            return ConnectorResultV1(
                source=source_name,
                duration=duration,
                jobs_fetched=len(data),
                failures=0,
                status="Success",
                raw_items=data
            )
        else:
            logger.warning(f"LeverConnector: failed to fetch jobs for '{board}'")
            return ConnectorResultV1(
                source=source_name,
                duration=duration,
                jobs_fetched=0,
                failures=1,
                status="Failed",
                raw_items=[]
            )
