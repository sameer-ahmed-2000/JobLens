import os
import sys
import logging
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s - %(message)s")
logger = logging.getLogger("test_embedding_worker")

from app.database import Base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.repositories.uow import UnitOfWork
from app.services.seeder import seed_if_empty
from app.services.ingestion.queue import embedding_queue
from app.services.ingestion.embedding_worker import EmbeddingWorker

test_engine = create_engine("sqlite:///:memory:", echo=False)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

class TestUnitOfWork(UnitOfWork):
    def __init__(self):
        super().__init__(session_factory=TestSessionLocal)

def test_embedding_worker_processing():
    logger.info("=== Starting Test: Independent EmbeddingWorker Processing ===")
    Base.metadata.create_all(bind=test_engine)
    seed_if_empty(uow_factory=TestUnitOfWork)

    # Get a seeded job that has an embedding
    with TestUnitOfWork() as uow:
        jobs = uow.jobs.get_all_postings()
        assert len(jobs) > 0
        target_job = jobs[0]
        job_id = target_job.id
    # Clear stream if it's Redis-backed to ensure test isolation
    if hasattr(embedding_queue, "client") and hasattr(embedding_queue, "stream_key"):
        embedding_queue.client.delete(embedding_queue.stream_key)
        if hasattr(embedding_queue, "retry_hash_key"):
            embedding_queue.client.delete(embedding_queue.retry_hash_key)
        try:
            embedding_queue.client.xgroup_create(embedding_queue.stream_key, embedding_queue.group_name, id="$", mkstream=True)
        except Exception:
            pass

    # Enqueue job ID into embedding queue
    embedding_queue.enqueue(job_id)
    assert embedding_queue.size() == 1

    worker = EmbeddingWorker(queue=embedding_queue)

    with patch("app.services.ingestion.embedding_worker.UnitOfWork", TestUnitOfWork), \
         patch("app.services.ingestion.scoring_worker.scoring_worker.enqueue"), \
         patch("app.services.embeddings.SentenceTransformerEmbeddingService.embed_job") as mock_embed:
        mock_embed.return_value = [0.1] * 384
        
        processed = worker.process_once(max_batch=5)

        assert processed == 1
        if embedding_queue.queue_backend == "redis":
            pending_info = embedding_queue.client.xpending(embedding_queue.stream_key, embedding_queue.group_name)
            assert pending_info.get("pending", 0) == 0, f"Expected 0 pending messages, got {pending_info.get('pending')}"
        else:
            assert embedding_queue.size() == 0

        # Verify DB record was updated with embedding
        from app.models.orm import JobORM
        with TestUnitOfWork() as uow:
            updated_job = uow.session.query(JobORM).filter(JobORM.id == job_id).first()
            assert updated_job is not None
            assert updated_job.embedding is not None
            assert len(updated_job.embedding) == 384

    logger.info("=== Test Passed: EmbeddingWorker dequeued job and stored 384-dim vector in PostgreSQL! ===\n")

if __name__ == "__main__":
    try:
        test_embedding_worker_processing()
        logger.info("=== EMBEDDING WORKER TEST PASSED SUCCESSFULLY! ===")
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        sys.exit(1)
