import time
import logging
import threading
import socket
import os
from typing import Optional, List, Dict
from app.config import settings
from app.services.ingestion.queue import embedding_queue, IEmbeddingQueue, InMemoryEmbeddingQueue
from app.services.embeddings import SentenceTransformerEmbeddingService
from app.repositories.uow import UnitOfWork

logger = logging.getLogger("embedding_worker")

class EmbeddingWorker:
    def __init__(self, queue: IEmbeddingQueue = embedding_queue, poll_interval: float = 2.0):
        self.queue = queue
        self.poll_interval = poll_interval
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._recovery_thread: Optional[threading.Thread] = None
        self._embedding_service = None
        
        # Unique consumer name: worker-{hostname}-{pid}
        self.consumer_name = f"worker-{socket.gethostname()}-{os.getpid()}"
        
        # Local tracking map for failed entries in this process: entry_id -> failed_timestamp
        # Used to scan past locally failed pending messages for 60 seconds
        self._failed_entries: Dict[str, float] = {}

    def _get_embedding_service(self):
        if self._embedding_service is None:
            self._embedding_service = SentenceTransformerEmbeddingService()
        return self._embedding_service

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        
        # Start normal worker loop
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="EmbeddingWorkerThread")
        self._thread.start()
        
        # Start recovery watchdog loop ONLY if queue backend is Redis
        if self.queue.queue_backend == "redis":
            self._recovery_thread = threading.Thread(target=self._run_recovery_loop, daemon=True, name="EmbeddingRecoveryThread")
            self._recovery_thread.start()
            logger.info("EmbeddingWorker started independent recovery loop watchdog thread.")
        
        logger.info(f"EmbeddingWorker {self.consumer_name} started background processing loop.")

    def stop(self) -> None:
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3.0)
        if self._recovery_thread and self._recovery_thread.is_alive():
            self._recovery_thread.join(timeout=3.0)
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

    def _run_recovery_loop(self) -> None:
        while self._running:
            try:
                self.recover_stuck_jobs()
            except Exception as e:
                logger.error(f"Error in EmbeddingWorker recovery watchdog loop: {e}", exc_info=True)
            
            # Sleep in small increments of 1 second so worker can shut down cleanly without waiting 30s
            for _ in range(30):
                if not self._running:
                    break
                time.sleep(1.0)

    def process_once(self, max_batch: int = 10) -> int:
        """Process up to max_batch job IDs from the queue. Returns number of jobs processed."""
        # Clean up failed entries that were recorded > 60s ago
        now = time.time()
        expired_eids = [eid for eid, t in self._failed_entries.items() if now - t >= 60.0]
        for eid in expired_eids:
            self._failed_entries.pop(eid, None)

        processed_count = 0
        for _ in range(max_batch):
            exclude = list(self._failed_entries.keys())
            res = self.queue.dequeue(consumer_name=self.consumer_name, exclude_ids=exclude)
            if not res:
                break

            entry_id, job_id = res

            try:
                success = self.process_job_by_id(job_id)
                if success:
                    self.queue.ack(entry_id)
                    processed_count += 1
                else:
                    # Failed processing (e.g. job_id not in DB), track in local list to avoid hot loops
                    logger.warning(f"EmbeddingWorker: Job processing failed for '{job_id}' (Entry: {entry_id})")
                    self._failed_entries[entry_id] = time.time()
                    if self.queue.queue_backend == "in_memory_fallback":
                        self.queue.enqueue(job_id)
            except Exception as e:
                logger.error(f"EmbeddingWorker: Exception processing job '{job_id}' (Entry: {entry_id}): {e}", exc_info=True)
                self._failed_entries[entry_id] = time.time()
                if self.queue.queue_backend == "in_memory_fallback":
                    self.queue.enqueue(job_id)

        return processed_count

    def process_job_by_id(self, job_id: str) -> bool:
        """Compute the embedding for a single job ID and upsert to database."""
        with UnitOfWork() as uow:
            posting = uow.jobs.get_by_id(job_id)
            if not posting:
                logger.warning(f"EmbeddingWorker: job_id '{job_id}' not found in DB.")
                return False

            embed_service = self._get_embedding_service()
            text_to_embed = f"Title: {posting.title}. Company: {posting.company}. Description: {posting.description}"
            emb = embed_service.embed_job(text_to_embed)

            # Update database record with computed embedding
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
            logger.info(f"EmbeddingWorker: successfully computed and stored embedding for job '{posting.title}' at '{posting.company}'.")
            
            # Enqueue job ID for scoring match calculations
            try:
                from app.services.ingestion.scoring_worker import scoring_worker
                scoring_worker.enqueue(posting.id)
            except Exception as e:
                logger.error(f"EmbeddingWorker: Failed to enqueue job '{posting.id}' for scoring: {e}")

            return True

    def recover_stuck_jobs(self) -> None:
        """
        Scan and reclaim entries in PEL idle for > 60s.
        If entry exceeded max retries, route to DLQ.
        """
        if not hasattr(self.queue, "client") or not hasattr(self.queue, "stream_key"):
            return

        client = self.queue.client
        start_id = "0-0"

        while self._running:
            try:
                # XAUTOCLAIM key group consumer min-idle-time start [COUNT count]
                res = client.xautoclaim(
                    name=self.queue.stream_key,
                    groupname=self.queue.group_name,
                    consumername=self.consumer_name,
                    min_idle_time=60000,
                    start_id=start_id,
                    count=10
                )
            except Exception as e:
                logger.error(f"EmbeddingWorker Watchdog: XAUTOCLAIM command failed: {e}")
                break

            if not res:
                break

            next_start_id, claimed_entries, _ = res[:3]

            for entry_id, data in claimed_entries:
                job_id = data.get("job_id")
                if not job_id:
                    continue

                try:
                    attempts = client.hincrby(self.queue.retry_hash_key, job_id, 1)
                except Exception as e:
                    logger.error(f"EmbeddingWorker Watchdog: Failed to increment retry count for job '{job_id}': {e}")
                    attempts = 1

                logger.warning(f"EmbeddingWorker Watchdog: Claimed stuck job '{job_id}' (Entry: {entry_id}), retry attempt: {attempts}")

                if attempts > settings.embedding_max_retries:
                    logger.error(f"EmbeddingWorker Watchdog: Job '{job_id}' (Entry: {entry_id}) exceeded max retries ({settings.embedding_max_retries}). Moving to DLQ.")
                    try:
                        client.xadd(
                            self.queue.dlq_key,
                            {
                                "job_id": job_id,
                                "entry_id": entry_id,
                                "failed_at": str(time.time()),
                                "reason": "Max retries exceeded"
                            }
                        )
                        # ACK the message to clear it from stream/PEL
                        self.queue.ack(entry_id)
                    except Exception as e:
                        logger.error(f"EmbeddingWorker Watchdog: Failed to move job '{job_id}' to DLQ: {e}")
                else:
                    # Leave claimed: next time process_once runs, it scans PEL and picks it up
                    pass

            if next_start_id == "0-0" or next_start_id == start_id:
                break
            start_id = next_start_id

# Global singleton worker for application use
embedding_worker = EmbeddingWorker()
