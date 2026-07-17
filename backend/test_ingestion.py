import os
import sys
import logging
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s - %(message)s")
logger = logging.getLogger("test_ingestion")

from app.database import Base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.repositories.uow import UnitOfWork
from app.services.seeder import seed_if_empty
from app.services.ingestion.connectors import GreenhouseConnector, LeverConnector, AshbyConnector, ConnectorResultV1
from app.services.ingestion.normalizer import normalize_job
from app.services.ingestion.queue import embedding_queue
from app.services.ingestion.pipeline import run_ingestion_pipeline

test_engine = create_engine("sqlite:///:memory:", echo=False)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

class TestUnitOfWork(UnitOfWork):
    def __init__(self):
        super().__init__(session_factory=TestSessionLocal)

def test_1_connectors_and_retry():
    logger.info("=== Starting Test 1: Connector Resilience & Retry Policy ===")
    gh = GreenhouseConnector(timeout=1.0, max_retries=1)
    
    # Test retry on failed HTTP GET
    with patch("httpx.Client.get") as mock_get:
        mock_get.side_effect = Exception("Timeout simulated")
        res = gh.fetch({"source_type": "Greenhouse", "board": "testboard", "name": "Greenhouse:testboard"})
        assert res.status == "Failed"
        assert res.failures == 1
        assert mock_get.call_count == 2  # Initial + 1 retry

    # Test successful fetch
    with patch("httpx.Client.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"jobs": [{"id": 1, "title": "AI Engineer", "absolute_url": "http://job.1", "content": "<p>Build RAG</p>"}]}
        mock_get.return_value = mock_resp
        res = gh.fetch({"source_type": "Greenhouse", "board": "testboard", "name": "Greenhouse:testboard"})
        assert res.status == "Success"
        assert res.jobs_fetched == 1
        assert res.raw_items[0]["title"] == "AI Engineer"

    logger.info("=== Test 1 Passed: Connectors handle retry policy and versioned results! ===\n")

def test_2_normalization():
    logger.info("=== Starting Test 2: Normalization Across Boards ===")
    gh_raw = {"id": 101, "title": "LLM Engineer", "absolute_url": "https://gh/101", "content": "<b>Develop agents</b>"}
    gh_norm = normalize_job(gh_raw, "Greenhouse", "openai")
    assert gh_norm.title == "LLM Engineer"
    assert gh_norm.company == "Openai"
    assert gh_norm.description == "Develop agents"
    assert gh_norm.id == "gh-openai-101"

    lev_raw = {"id": "202", "text": "Senior ML Ops", "hostedUrl": "https://lev/202", "descriptionPlain": "Kubernetes and PyTorch"}
    lev_norm = normalize_job(lev_raw, "Lever", "netflix")
    assert lev_norm.title == "Senior ML Ops"
    assert lev_norm.company == "Netflix"
    assert lev_norm.description == "Kubernetes and PyTorch"

    ash_raw = {"id": "303", "title": "Staff Researcher", "jobUrl": "https://ash/303", "descriptionHtml": "<p>Deep learning</p>"}
    ash_norm = normalize_job(ash_raw, "Ashby", "vercel")
    assert ash_norm.title == "Staff Researcher"
    assert ash_norm.company == "Vercel"
    assert ash_norm.description == "Deep learning"

    logger.info("=== Test 2 Passed: Normalizer cleans HTML and standardizes Pydantic RawPosting models! ===\n")

def test_3_pipeline_and_deduplication():
    logger.info("=== Starting Test 3: Pipeline Filtering, Deterministic Dedup & Incremental Storage ===")
    Base.metadata.create_all(bind=test_engine)
    seed_if_empty(uow_factory=TestUnitOfWork)

    from app.config import settings
    orig_adzuna = settings.adzuna_enabled
    orig_remotive = settings.remotive_enabled
    orig_arbeitnow = settings.arbeitnow_enabled
    settings.adzuna_enabled = False
    settings.remotive_enabled = False
    settings.arbeitnow_enabled = False

    # Ensure all Greenhouse sources are active in the test DB for the 9 jobs assertion
    with TestUnitOfWork() as uow:
        from app.models.orm import JobSourceORM
        uow.session.query(JobSourceORM).filter(JobSourceORM.name.like("Greenhouse:%")).update({"is_active": True})
        uow.commit()

    mock_gh_jobs = [
        {"id": 10, "title": "AI Engineer - Remote", "absolute_url": "https://gh/10", "content": "Build LangGraph pipelines using Python.", "location": "Remote"},
        {"id": 11, "title": "AI Engineer - Remote", "absolute_url": "https://gh/11", "content": "Duplicate title and company!", "location": "Remote"},
        {"id": 12, "title": "Frontend Chef", "absolute_url": "https://gh/12", "content": "Cook burgers.", "location": "New York"}
    ]

    try:
        with patch("app.services.ingestion.pipeline.UnitOfWork", TestUnitOfWork), \
             patch("app.services.ingestion.source_registry.UnitOfWork", TestUnitOfWork), \
             patch.object(GreenhouseConnector, "fetch", return_value=ConnectorResultV1(source="Greenhouse:openai", duration=0.1, jobs_fetched=3, failures=0, status="Success", raw_items=mock_gh_jobs)), \
             patch.object(LeverConnector, "fetch", return_value=ConnectorResultV1(source="Lever:netflix", duration=0.1, jobs_fetched=0, failures=0, status="Success", raw_items=[])), \
             patch.object(AshbyConnector, "fetch", return_value=ConnectorResultV1(source="Ashby:vercel", duration=0.1, jobs_fetched=0, failures=0, status="Success", raw_items=[])):
            
            # We filter by keyword "LangGraph" or "AI Engineer" and location "Remote"
            stats = run_ingestion_pipeline(keywords=["LangGraph"], location="Remote")
            assert stats["total_fetched"] == 9  # 3 greenhouse boards * 3 jobs each
            # Job 10 matches LangGraph & Remote -> Inserted (1 on first board)
            # On subsequent boards/jobs, duplicates removed
            assert stats["total_inserted"] == 1
            assert stats["total_duplicates"] >= 1
    finally:
        settings.adzuna_enabled = orig_adzuna
        settings.remotive_enabled = orig_remotive
        settings.arbeitnow_enabled = orig_arbeitnow


        # Check queue has job ID
        q_size = embedding_queue.size()
        assert q_size >= 1, "New job was not enqueued for embedding!"

        # Check IngestionRunORM log in PostgreSQL
        with TestUnitOfWork() as uow:
            runs = uow.ingestion_runs.get_latest(limit=10)
            assert len(runs) > 0
            assert any(r["jobs_inserted"] >= 1 for r in runs)
            assert any(r["status"] == "Success" for r in runs)

    logger.info("=== Test 3 Passed: Pipeline filtered, deduplicated, updated DB incrementally, and logged IngestionRunORM! ===\n")

if __name__ == "__main__":
    try:
        test_1_connectors_and_retry()
        test_2_normalization()
        test_3_pipeline_and_deduplication()
        logger.info("=== ALL 3 INGESTION PIPELINE TESTS PASSED SUCCESSFULLY! ===")
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        sys.exit(1)
