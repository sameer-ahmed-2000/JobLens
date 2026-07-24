import os
import sys
import logging
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("test_rate_limiting")

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.database import Base
import app.models.orm
from app.repositories.uow import UnitOfWork
from app.main import app
from app.config import settings
from app.rate_limiter import limiter

test_engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool, echo=False)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

def test_per_source_polling_intervals():
    logger.info("=== Starting Test: Item 7 — Per-Source Polling Intervals ===")
    Base.metadata.create_all(bind=test_engine)

    from app.services.ingestion.source_registry import SourceRegistry
    from app.services.ingestion.pipeline import run_ingestion_pipeline
    from app.models.orm import JobSourceORM
    from datetime import datetime, timedelta

    # Insert test job sources into DB with different poll intervals
    with TestSessionLocal() as session:
        session.query(JobSourceORM).delete()
        s_fast = JobSourceORM(
            id="src-1", name="Jooble:search", url="aggregator", is_active=True,
            poll_interval_minutes=5, last_fetched_at=datetime.utcnow() - timedelta(minutes=10)
        )
        s_slow = JobSourceORM(
            id="src-2", name="Greenhouse:openai", url="openai", is_active=True,
            poll_interval_minutes=60, last_fetched_at=datetime.utcnow() - timedelta(minutes=5)
        )
        session.add(s_fast)
        session.add(s_slow)
        session.commit()

    class TestUOW(UnitOfWork):
        def __init__(self):
            super().__init__(session_factory=TestSessionLocal)

    with patch("app.services.ingestion.pipeline.UnitOfWork", TestUOW), \
         patch("app.services.ingestion.source_registry.UnitOfWork", TestUOW), \
         patch("app.services.ingestion.connectors.JoobleConnector.fetch") as mock_jb_fetch, \
         patch("app.services.ingestion.connectors.GreenhouseConnector.fetch") as mock_gh_fetch:

        from app.services.ingestion.connectors import ConnectorResultV1
        mock_jb_fetch.return_value = ConnectorResultV1(source="Jooble:search", duration=0.1, jobs_fetched=0, failures=0, status="Success", raw_items=[])
        mock_gh_fetch.return_value = ConnectorResultV1(source="Greenhouse:openai", duration=0.1, jobs_fetched=0, failures=0, status="Success", raw_items=[])

        # Execute unforced pipeline run
        run_ingestion_pipeline(keywords=["python"], location="Remote", force=False)

        # Jooble (last run 10m ago >= 5m interval) SHOULD be polled
        assert mock_jb_fetch.called, "Jooble should have been polled (10m elapsed >= 5m interval)!"
        # Greenhouse (last run 5m ago < 60m interval) SHOULD be skipped
        assert not mock_gh_fetch.called, "Greenhouse should have been skipped (5m elapsed < 60m interval)!"

        logger.info("Passed: Per-source polling intervals correctly filtered source execution!")


def test_api_rate_limiting():
    logger.info("=== Starting Test: Item 8 — API Rate Limiting ===")
    Base.metadata.create_all(bind=test_engine)

    from app.services.seeder import seed_if_empty
    class TestUOW(UnitOfWork):
        def __init__(self):
            super().__init__(session_factory=TestSessionLocal)

    seed_if_empty(uow_factory=TestUOW)

    def mock_uow_init(self, session_factory=None):
        self.session_factory = TestSessionLocal
        self.session = None

    with patch.object(UnitOfWork, "__init__", mock_uow_init):
        client = TestClient(app)
        headers = {"Authorization": "Bearer default-user-token"}
        success_count = 0
        rate_limited = False

        # Send request burst to /api/stream/ticket (limit: 30/minute)
        for i in range(35):
            resp = client.post("/api/stream/ticket", headers=headers)
            if resp.status_code == 200:
                success_count += 1
            elif resp.status_code == 429:
                rate_limited = True
                break

        assert rate_limited, "Rate limiting should have triggered 429 response after threshold exceeded!"
        logger.info(f"Passed: Rate limiting correctly enforced! ({success_count} allowed requests before 429 Too Many Requests)")


if __name__ == "__main__":
    try:
        test_per_source_polling_intervals()
        test_api_rate_limiting()
        logger.info("=== ALL TESTS FOR ITEMS 7 & 8 PASSED SUCCESSFULLY! ===")
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        sys.exit(1)
