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
    """
    Base class for all ingestion connectors.

    Each connector has its own configurable rate-limit and retry policy so that
    different source APIs (Adzuna, Remotive, Arbeitnow, Greenhouse, etc.) are
    throttled independently. A uniform scheduler tick does not mean all connectors
    must fire at the same effective rate — override these in subclasses as needed.

    Attributes:
        timeout:          HTTP request timeout in seconds.
        max_retries:      Number of additional attempts after the first failure.
        rate_limit_rps:   Maximum requests per second to this source (applied as a
                          minimum inter-request delay). Default 1.0 = 1 req/s.
        backoff_base:     Base delay in seconds for exponential back-off between
                          retries. Attempt n waits backoff_base * 2^(n-1) seconds.
    """

    def __init__(
        self,
        timeout: float = 10.0,
        max_retries: int = 2,
        rate_limit_rps: float = 1.0,
        backoff_base: float = 1.0,
    ):
        self.timeout = timeout
        self.max_retries = max_retries
        # Minimum seconds to wait between successive requests to this source.
        self._min_request_interval = 1.0 / rate_limit_rps if rate_limit_rps > 0 else 0.0
        self._backoff_base = backoff_base
        self._last_request_at: float = 0.0  # epoch seconds of the last request

    @abstractmethod
    def fetch(self, source_config: Dict[str, Any]) -> ConnectorResultV1:
        """Fetch raw job postings from the given source configuration."""
        pass

    def _throttle(self) -> None:
        """Block until the per-source rate limit allows the next request."""
        if self._min_request_interval <= 0:
            return
        elapsed = time.monotonic() - self._last_request_at
        wait = self._min_request_interval - elapsed
        if wait > 0:
            time.sleep(wait)

    def _http_get_with_retry(
        self, url: str, params: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Perform an HTTP GET with per-source rate limiting and exponential back-off.

        Rate limiting: enforces self._min_request_interval between requests.
        Back-off: on failure, waits backoff_base * 2^(attempt-1) seconds before
        the next attempt, capped at max_retries additional attempts.
        """
        attempt = 0
        while attempt <= self.max_retries:
            self._throttle()
            self._last_request_at = time.monotonic()
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    response = client.get(url, params=params)
                    if response.status_code == 200:
                        return response.json()
                    elif response.status_code == 429:
                        # Explicit rate-limit response from the source — back off harder
                        retry_after = float(response.headers.get("Retry-After", self._backoff_base * (2 ** attempt)))
                        logger.warning(
                            f"Rate-limited by {url} (HTTP 429). Waiting {retry_after:.1f}s "
                            f"before attempt {attempt + 2}/{self.max_retries + 1}."
                        )
                        time.sleep(retry_after)
                    else:
                        logger.warning(
                            f"HTTP GET {url} returned status {response.status_code} "
                            f"(attempt {attempt + 1}/{self.max_retries + 1})."
                        )
            except Exception as e:
                logger.warning(
                    f"Attempt {attempt + 1}/{self.max_retries + 1} failed for {url}: {e}"
                )

            attempt += 1
            if attempt <= self.max_retries:
                backoff = self._backoff_base * (2 ** (attempt - 1))
                logger.debug(f"Back-off: waiting {backoff:.2f}s before retry {attempt + 1}.")
                time.sleep(backoff)

        logger.error(f"All {self.max_retries + 1} attempts failed for GET {url}")
        return None

    def _http_post_with_retry(
        self, url: str, json_body: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Same rate-limiting/back-off contract as _http_get_with_retry, for sources
        (e.g. Jooble) whose search endpoint requires POST with a JSON body instead
        of query params.
        """
        attempt = 0
        while attempt <= self.max_retries:
            self._throttle()
            self._last_request_at = time.monotonic()
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    response = client.post(url, json=json_body)
                    if response.status_code == 200:
                        return response.json()
                    elif response.status_code == 429:
                        retry_after = float(response.headers.get("Retry-After", self._backoff_base * (2 ** attempt)))
                        logger.warning(
                            f"Rate-limited by {url} (HTTP 429). Waiting {retry_after:.1f}s "
                            f"before attempt {attempt + 2}/{self.max_retries + 1}."
                        )
                        time.sleep(retry_after)
                    else:
                        logger.warning(
                            f"HTTP POST {url} returned status {response.status_code} "
                            f"(attempt {attempt + 1}/{self.max_retries + 1})."
                        )
            except Exception as e:
                logger.warning(
                    f"Attempt {attempt + 1}/{self.max_retries + 1} failed for POST {url}: {e}"
                )

            attempt += 1
            if attempt <= self.max_retries:
                backoff = self._backoff_base * (2 ** (attempt - 1))
                logger.debug(f"Back-off: waiting {backoff:.2f}s before retry {attempt + 1}.")
                time.sleep(backoff)

        logger.error(f"All {self.max_retries + 1} attempts failed for POST {url}")
        return None
