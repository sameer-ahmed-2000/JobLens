import time
import logging
import threading
from typing import Optional
from app.services.ingestion.queue import embedding_queue, IEmbeddingQueue
from app.services.embeddings import SentenceTransformerEmbeddingService
from app.repositories.uow import UnitOfWork

logger = logging.getLogger("embedding_worker")

class EmbeddingWorker:
    def __init__(self, queue: IEmbeddingQueue = embedding_queue, poll_interval: float = 2.0):
        self.queue = queue
        self.poll_interval = poll_interval
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._embedding_service = None

    def _get_embedding_service(self):
        if self._embedding_service is None:
            self._embedding_service = SentenceTransformerEmbeddingService()
        return self._embedding_service

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="EmbeddingWorkerThread")
        self._thread.start()
        logger.info("EmbeddingWorker started independent background loop.")

    def stop(self) -> None:
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3.0)
        logger.info("EmbeddingWorker stopped.")

    def _run_loop(self) -> None:
        while self._running:
            try:
                processed = self.process_once(max_batch=5)
                if processed == 0:
                    time.sleep(self.poll_interval)
            except Exception as e:
                logger.error(f"Error in EmbeddingWorker loop: {e}", exc_info=True)
                time.sleep(self.poll_interval)

    def process_once(self, max_batch: int = 10) -> int:
        """Process up to max_batch job IDs from the queue. Returns number of jobs processed."""
        processed_count = 0
        for _ in range(max_batch):
            job_id = self.queue.dequeue()
            if not job_id:
                break

            try:
                with UnitOfWork() as uow:
                    posting = uow.jobs.get_by_id(job_id)
                    if not posting:
                        logger.warning(f"EmbeddingWorker: job_id '{job_id}' not found in DB.")
                        continue

                    embed_service = self._get_embedding_service()
                    text_to_embed = f"Title: {posting.title}. Company: {posting.company}. Description: {posting.description}"
                    emb = embed_service.embed_job(text_to_embed)

                    # Update database record with computed embedding
                    # We look up company_id or pass required fields to upsert
                    uow.jobs.upsert(
                        title=posting.title,
                        company_name=posting.company,
                        description=posting.description,
                        url=posting.url,
                        source=posting.source,
                        job_id=posting.id,
                        embedding=emb.tolist() if hasattr(emb, "tolist") else list(emb)
                    )
                    uow.commit()
                    processed_count += 1
                    logger.info(f"EmbeddingWorker: successfully computed and stored embedding for job '{posting.title}' at '{posting.company}'.")
            except Exception as e:
                logger.error(f"EmbeddingWorker failed for job '{job_id}': {e}", exc_info=True)
                # Re-enqueue on failure so we don't lose it
                self.queue.enqueue(job_id)

        return processed_count

# Global singleton worker for application use
embedding_worker = EmbeddingWorker()
