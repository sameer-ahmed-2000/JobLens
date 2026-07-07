import time
import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
import httpx

logger = logging.getLogger(__name__)

class ConnectorResultV1(BaseModel):
    source: str
    duration: float
    jobs_fetched: int
    failures: int
    status: str  # "Success", "Failed", "Partial"
    raw_items: List[Dict[str, Any]] = Field(default_factory=list)

class BaseConnector(ABC):
    def __init__(self, timeout: float = 10.0, max_retries: int = 2):
        self.timeout = timeout
        self.max_retries = max_retries

    @abstractmethod
    def fetch(self, source_config: Dict[str, Any]) -> ConnectorResultV1:
        """Fetch raw job postings from the given source configuration."""
        pass

    def _http_get_with_retry(self, url: str, params: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """Perform HTTP GET request with retry resilience policy (2 retries for transient failures)."""
        attempt = 0
        while attempt <= self.max_retries:
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    response = client.get(url, params=params)
                    if response.status_code == 200:
                        return response.json()
                    else:
                        logger.warning(f"HTTP GET {url} returned status code {response.status_code}")
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1}/{self.max_retries + 1} failed for {url}: {e}")
            attempt += 1
            if attempt <= self.max_retries:
                time.sleep(0.01 * attempt)
        logger.error(f"All {self.max_retries + 1} attempts failed for GET {url}")
        return None
