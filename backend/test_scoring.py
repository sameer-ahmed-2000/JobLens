import os
import sys
import time
import logging
import json
from unittest.mock import patch, MagicMock, ANY, PropertyMock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s - %(message)s")
logger = logging.getLogger("test_scoring")

from app.database import Base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.repositories.uow import UnitOfWork
from app.services.seeder import seed_if_empty
from app.services.scoring_service import ScoringService, ActiveResumesCache
from app.services.ingestion.scoring_worker import ScoringWorker
from app.models.orm import UserORM, ResumeORM, JobORM, JobMatchORM
from backfill_scores import run_backfill

# Setup test DB (SQLite in-memory)
test_engine = create_engine("sqlite:///:memory:", echo=False)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

class TestUnitOfWork(UnitOfWork):
    def __init__(self):
        super().__init__(session_factory=TestSessionLocal)

def setup_db():
    Base.metadata.create_all(bind=test_engine)
    seed_if_empty(uow_factory=TestUnitOfWork)

def test_active_resumes_cache():
    logger.info("=== Running Test: ActiveResumesCache ===")
    setup_db()

    with patch("app.repositories.uow.UnitOfWork", TestUnitOfWork), \
         patch("app.services.scoring_service.UnitOfWork", TestUnitOfWork):
        cache = ActiveResumesCache(refresh_interval=1.0)
        cache.refresh()
        
        data = cache.get_all()
        assert len(data) > 0, "Cache should load at least one active user/resume."
        
        for user_id, user_data in data.items():
            assert "embedding" in user_data
            assert len(user_data["embedding"]) == 384
            assert "display_threshold" in user_data
            assert "notify_threshold" in user_data
            logger.info(f"Loaded cache for user {user_id}: threshold={user_data['display_threshold']}")
            
        # Verify atomic swap thread safety
        # Re-populating must produce a new dict object
        old_cache_obj = cache._cache
        cache.refresh()
        new_cache_obj = cache._cache
        assert old_cache_obj is not new_cache_obj, "Cache update must atomically assign a new dict instance."

    logger.info("=== ActiveResumesCache Test Passed ===")

def test_scoring_service_and_per_user_events():
    logger.info("=== Running Test: ScoringService & Per-User Events ===")
    setup_db()

    with TestUnitOfWork() as uow:
        # Create a user with known display threshold
        user = uow.session.query(UserORM).first()
        user.display_threshold = 0.5
        user_id = user.id
        
        # Get active resume
        resume = uow.session.query(ResumeORM).filter(ResumeORM.user_id == user_id).first()
        resume.embedding = [0.1] * 384
        
        # Create a job with embedding
        job = JobORM(
            title="Test AI Engineer",
            description="Looking for an AI engineer with strong skills in Python.",
            url="https://example.com/test-ai-job",
            embedding=[0.1] * 384
        )
        uow.session.add(job)
        uow.commit()
        job_id = job.id

    with patch("app.repositories.uow.UnitOfWork", TestUnitOfWork), \
         patch("app.services.scoring_service.UnitOfWork", TestUnitOfWork), \
         patch("app.services.ingestion.queue.InMemoryEmbeddingQueue.queue_backend", new_callable=PropertyMock, return_value="redis"), \
         patch("app.services.ingestion.queue.embedding_queue.client", create=True) as mock_redis_client:
         
        service = ScoringService(refresh_interval=60.0)
        service.cache.refresh()
        
        # Score the job (score should be 1.0 since embeddings are identical [0.1]*384)
        service.score_job_for_all_users(job_id, publish_events=True)
        
        # Check that DB now has a match
        with TestUnitOfWork() as uow:
            match = uow.session.query(JobMatchORM).filter(
                JobMatchORM.user_id == user_id,
                JobMatchORM.job_id == job_id
            ).first()
            assert match is not None
            assert match.score == 1.0
            
        # Check event publication on user-specific channel
        expected_channel = f"job_events:{user_id}"
        mock_redis_client.publish.assert_called_once()
        called_args = mock_redis_client.publish.call_args
        assert called_args[0][0] == expected_channel
        event_payload = json.loads(called_args[0][1])
        assert event_payload["type"] == "new_match"
        assert event_payload["job_match_id"] is not None
        assert event_payload["title"] == "Test AI Engineer"
        assert event_payload["company"] == "Unknown Company"
        assert event_payload["score"] == 1.0
        assert event_payload["url"] == "https://example.com/test-ai-job"
        assert event_payload["source"] == "Live"

    logger.info("=== ScoringService & Per-User Events Test Passed ===")

def test_scoring_worker_fallback_warning():
    logger.info("=== Running Test: ScoringWorker Inline Fallback ===")
    setup_db()

    with patch("app.services.ingestion.scoring_worker.embedding_queue") as mock_queue, \
         patch("app.repositories.uow.UnitOfWork", TestUnitOfWork), \
         patch("app.services.scoring_service.UnitOfWork", TestUnitOfWork):
        # Simulate in-memory fallback
        mock_queue.queue_backend = "in_memory_fallback"
        
        worker = ScoringWorker()
        
        # Capture warning logs
        with patch("app.services.ingestion.scoring_worker.logger") as mock_logger:
            worker.start()
            mock_logger.warning.assert_any_call(
                "WARNING: In-memory fallback mode active. Jobs will be scored synchronously on enqueue. "
                "This degraded mode impacts ingestion throughput."
            )
            worker.stop()

    logger.info("=== ScoringWorker Inline Fallback Test Passed ===")

def test_lazy_rationale_and_ownership():
    logger.info("=== Running Test: Lazy Rationale and Ownership ===")
    setup_db()
    
    from fastapi import HTTPException
    import asyncio
    from app.routes.api import get_match_detail
    
    # Setup test users
    with TestUnitOfWork() as uow:
        user1 = uow.users.create(name="User 1", email="user1@example.com")
        user2 = uow.users.create(name="User 2", email="user2@example.com")
        
        job = JobORM(
            title="Senior React Developer",
            description="Need React and TypeScript expert.",
            url="https://example.com/react-dev",
            embedding=[0.2] * 384
        )
        uow.session.add(job)
        uow.commit()
        job_id = job.id
        
        # Create matches without rationales (rationale is None/empty)
        match1 = JobMatchORM(user_id=user1["id"], job_id=job_id, score=0.8, rationale=None)
        match2 = JobMatchORM(user_id=user2["id"], job_id=job_id, score=0.85, rationale=None)
        uow.session.add(match1)
        uow.session.add(match2)
        uow.commit()
        
        match1_id = match1.id
        match2_id = match2.id
        
    with patch("app.repositories.uow.UnitOfWork", TestUnitOfWork), \
         patch("app.services.llm_router.llm_router.generate", return_value="Generates typescript rationale.") as mock_generate:
         
        # 1. User 1 accesses Match 1 (Success + Generate rationale)
        res = asyncio.run(get_match_detail(match_id=match1_id, current_user_id=user1["id"]))
        assert res["fit_rationale"] == "Generates typescript rationale."
        mock_generate.assert_called_once()
        
        # Verify DB has updated rationale
        with TestUnitOfWork() as uow:
            db_match1 = uow.session.query(JobMatchORM).filter(JobMatchORM.id == match1_id).first()
            assert db_match1.rationale == "Generates typescript rationale."
            
        # 2. User 1 accesses Match 1 again (Cached - no LLM call)
        mock_generate.reset_mock()
        res_cached = asyncio.run(get_match_detail(match_id=match1_id, current_user_id=user1["id"]))
        assert res_cached["fit_rationale"] == "Generates typescript rationale."
        mock_generate.assert_not_called()
        
        # 3. User 2 accesses Match 1 (Ownership violation -> raise 404, not 403)
        try:
            asyncio.run(get_match_detail(match_id=match1_id, current_user_id=user2["id"]))
            assert False, "Should raise 404 error on ownership mismatch."
        except HTTPException as exc:
            assert exc.status_code == 404
            assert exc.detail == "Job match not found."

    logger.info("=== Lazy Rationale & Ownership Test Passed ===")

def test_backfill_suppress_events():
    logger.info("=== Running Test: Backfill Event Suppression ===")
    setup_db()
    
    with TestUnitOfWork() as uow:
        user = uow.session.query(UserORM).first()
        user_id = user.id
        
        resume = uow.session.query(ResumeORM).filter(ResumeORM.user_id == user_id).first()
        resume.embedding = [0.2] * 384
        
        job = JobORM(
            title="Unscored Job",
            description="Python software engineer",
            url="https://example.com/unscored-job",
            embedding=[0.2] * 384
        )
        uow.session.add(job)
        uow.commit()
        job_id = job.id

    with patch("app.repositories.uow.UnitOfWork", TestUnitOfWork), \
         patch("app.services.scoring_service.UnitOfWork", TestUnitOfWork), \
         patch("backfill_scores.UnitOfWork", TestUnitOfWork), \
         patch("app.services.ingestion.queue.InMemoryEmbeddingQueue.queue_backend", new_callable=PropertyMock, return_value="redis"), \
         patch("app.services.ingestion.queue.embedding_queue.client", create=True) as mock_redis_client:
         
         # Run backfill
         run_backfill()
         
         # Assert score is updated in database
         with TestUnitOfWork() as uow:
             match = uow.session.query(JobMatchORM).filter(
                 JobMatchORM.user_id == user_id,
                 JobMatchORM.job_id == job_id
             ).first()
             assert match is not None
             assert match.score == 1.0
             
         # Event publishing should NOT be called (backfill suppress events)
         mock_redis_client.publish.assert_not_called()

    logger.info("=== Backfill Event Suppression Test Passed ===")

if __name__ == "__main__":
    test_active_resumes_cache()
    test_scoring_service_and_per_user_events()
    test_scoring_worker_fallback_warning()
    test_lazy_rationale_and_ownership()
    test_backfill_suppress_events()
    logger.info("\n=== ALL SCORING AND INGEST PHASE 3 TESTS PASSED! ===")
