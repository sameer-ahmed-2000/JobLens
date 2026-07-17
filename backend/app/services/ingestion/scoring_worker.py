import time
import logging
import threading
import socket
import os
from typing import Optional, List, Dict
import redis
from app.config import settings
from app.services.scoring_service import scoring_service
from app.services.ingestion.queue import embedding_queue

logger = logging.getLogger("scoring_worker")

class ScoringWorker:
    def __init__(self, poll_interval: float = 2.0):
        self.poll_interval = poll_interval
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self.scoring_service = scoring_service
        
        # Redis Stream configuration
        self.stream_key = "jobs:scoring:stream"
        self.group_name = "scoring_workers"
        self.consumer_name = f"scoring-worker-{socket.gethostname()}-{os.getpid()}"
        
        # Local tracking map for failed entries in this process: entry_id -> failed_timestamp
        # Used to scan past locally failed pending messages for 60 seconds
        self._failed_entries: Dict[str, float] = {}

    @property
    def is_redis(self) -> bool:
        return hasattr(embedding_queue, "queue_backend") and embedding_queue.queue_backend == "redis"

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        
        # Start the scoring service (cache refresh thread)
        self.scoring_service.start()
        
        # Create stream and group if Redis is active
        if self.is_redis:
            self._init_redis_group()
            # Start background consumer thread
            self._thread = threading.Thread(target=self._run_loop, daemon=True, name="ScoringWorkerThread")
            self._thread.start()
            logger.info(f"ScoringWorker {self.consumer_name} started background processing loop.")
        else:
            logger.warning(
                "WARNING: In-memory fallback mode active. Jobs will be scored synchronously on enqueue. "
                "This degraded mode impacts ingestion throughput."
            )

    def stop(self) -> None:
        self._running = False
        self.scoring_service.stop()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3.0)
        logger.info("ScoringWorker stopped.")

    def _init_redis_group(self) -> None:
        client = embedding_queue.client
        try:
            client.xgroup_create(self.stream_key, self.group_name, id="$", mkstream=True)
            logger.info(f"Created Redis stream '{self.stream_key}' and consumer group '{self.group_name}'")
        except redis.exceptions.ResponseError as e:
            if "BUSYGROUP" not in str(e):
                logger.error(f"Failed to create Redis consumer group '{self.group_name}' for stream '{self.stream_key}': {e}")

    def enqueue(self, job_id: str) -> None:
        """Enqueue a job ID for scoring match calculations."""
        if self.is_redis:
            try:
                embedding_queue.client.xadd(self.stream_key, {"job_id": job_id})
                logger.info(f"ScoringWorker: Enqueued job '{job_id}' to Redis stream '{self.stream_key}'.")
            except Exception as e:
                logger.error(f"ScoringWorker: Failed to enqueue job '{job_id}' to stream: {e}")
        else:
            # Inline synchronous processing for in-memory fallback
            logger.info(f"ScoringWorker: Running synchronous fallback scoring for job '{job_id}'...")
            try:
                self.scoring_service.score_job_for_all_users(job_id, publish_events=True)
            except Exception as e:
                logger.error(f"ScoringWorker: Synchronous fallback scoring failed for job '{job_id}': {e}")

    def _run_loop(self) -> None:
        while self._running:
            try:
                processed = self.process_once(max_batch=5)
                if processed == 0:
                    time.sleep(self.poll_interval)
            except Exception as e:
                logger.error(f"Error in ScoringWorker processing loop: {e}", exc_info=True)
                time.sleep(self.poll_interval)

    def process_once(self, max_batch: int = 10) -> int:
        """Process up to max_batch job IDs from the queue. Returns number of jobs processed."""
        if not self.is_redis:
            return 0  # In-memory runs synchronously on enqueue

        # Clean up failed entries that were recorded > 60s ago
        now = time.time()
        expired_eids = [eid for eid, t in self._failed_entries.items() if now - t >= 60.0]
        for eid in expired_eids:
            self._failed_entries.pop(eid, None)

        client = embedding_queue.client
        processed_count = 0

        for _ in range(max_batch):
            exclude = list(self._failed_entries.keys())
            res = self._dequeue(exclude_ids=exclude)
            if not res:
                break

            entry_id, job_id = res

            try:
                self.scoring_service.score_job_for_all_users(job_id, publish_events=True)
                client.xack(self.stream_key, self.group_name, entry_id)
                processed_count += 1
            except Exception as e:
                logger.error(f"ScoringWorker: Exception scoring job '{job_id}' (Entry: {entry_id}): {e}", exc_info=True)
                self._failed_entries[entry_id] = time.time()

        return processed_count

    def _dequeue(self, exclude_ids: Optional[List[str]] = None) -> Optional[tuple[str, str]]:
        if not self.is_redis:
            return None
        if exclude_ids is None:
            exclude_ids = []

        client = embedding_queue.client

        # 1. Try to read pending messages for this consumer (PEL scan)
        start_id = "0-0"
        while True:
            try:
                res = client.xreadgroup(
                    groupname=self.group_name,
                    consumername=self.consumer_name,
                    streams={self.stream_key: start_id},
                    count=1
                )
            except Exception as e:
                logger.error(f"ScoringWorker: Failed to read pending: {e}")
                break

            if not res:
                break
            try:
                stream_name, entries = res[0]
                if not entries:
                    break
                entry_id, data = entries[0]
                if entry_id in exclude_ids:
                    # Scan past this entry in the next iteration
                    start_id = entry_id
                    continue
                job_id = data.get("job_id")
                return entry_id, job_id
            except (IndexError, KeyError):
                break

        # 2. Read new messages using '>'
        try:
            res = client.xreadgroup(
                groupname=self.group_name,
                consumername=self.consumer_name,
                streams={self.stream_key: ">"},
                count=1,
                block=2000
            )
        except Exception as e:
            logger.error(f"ScoringWorker: Failed to read new: {e}")
            return None

        if res:
            try:
                stream_name, entries = res[0]
                if entries:
                    entry_id, data = entries[0]
                    job_id = data.get("job_id")
                    return entry_id, job_id
            except (IndexError, KeyError):
                pass

        return None

# Global singleton scoring worker
scoring_worker = ScoringWorker()
