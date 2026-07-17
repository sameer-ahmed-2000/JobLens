import collections
import logging
import os
import socket
import threading
from abc import ABC, abstractmethod
from typing import Optional, Tuple, List, Dict, Any
import redis
from app.config import settings

logger = logging.getLogger("embedding_queue")

class IEmbeddingQueue(ABC):
    @abstractmethod
    def enqueue(self, job_id: str) -> None:
        pass

    @abstractmethod
    def dequeue(self, consumer_name: Optional[str] = None, exclude_ids: Optional[List[str]] = None) -> Optional[Tuple[str, str]]:
        pass

    @abstractmethod
    def size(self) -> int:
        pass

    @abstractmethod
    def ack(self, entry_id: str) -> None:
        pass

    @abstractmethod
    def get_dlq_entries(self) -> List[Dict[str, Any]]:
        pass

    @property
    @abstractmethod
    def queue_backend(self) -> str:
        pass


class InMemoryEmbeddingQueue(IEmbeddingQueue):
    def __init__(self):
        self._queue = collections.deque()
        self._lock = threading.Lock()
        self._set = set()
        self._dlq: List[Dict[str, Any]] = []

    def enqueue(self, job_id: str) -> None:
        with self._lock:
            if job_id not in self._set:
                self._queue.append(job_id)
                self._set.add(job_id)

    def dequeue(self, consumer_name: Optional[str] = None, exclude_ids: Optional[List[str]] = None) -> Optional[Tuple[str, str]]:
        with self._lock:
            if not self._queue:
                return None
            
            # Since in-memory does not have a persistent stream, we scan the deque
            # to check if the first item is in exclude_ids. If it is, we skip it
            # (leaving it in the queue) and look for the next one.
            if exclude_ids:
                found_job_id = None
                for job_id in list(self._queue):
                    if job_id not in exclude_ids:
                        found_job_id = job_id
                        break
                if found_job_id is None:
                    return None
                
                self._queue.remove(found_job_id)
                self._set.discard(found_job_id)
                return (found_job_id, found_job_id)

            job_id = self._queue.popleft()
            self._set.discard(job_id)
            return (job_id, job_id)

    def size(self) -> int:
        with self._lock:
            return len(self._queue)

    def ack(self, entry_id: str) -> None:
        pass  # No-op for in-memory queue

    def get_dlq_entries(self) -> List[Dict[str, Any]]:
        return self._dlq

    def add_to_dlq(self, job_id: str, reason: str = "Max retries exceeded") -> None:
        with self._lock:
            self._dlq.append({
                "entry_id": job_id,
                "job_id": job_id,
                "failed_at": str(threading.get_ident()), # Dummy thread ID / timestamp
                "reason": reason
            })

    @property
    def queue_backend(self) -> str:
        return "in_memory_fallback"


class RedisStreamEmbeddingQueue(IEmbeddingQueue):
    def __init__(self, redis_url: str = settings.redis_url):
        self.client = redis.Redis.from_url(redis_url, decode_responses=True)
        # Force ping to ensure connection works; raises ConnectionError if down
        self.client.ping()

        self.stream_key = "jobs:embedding:stream"
        self.group_name = "embedding_workers"
        self.dlq_key = "jobs:embedding:dlq"
        self.retry_hash_key = "jobs:embedding:retries"
        self.maxlen = settings.embedding_stream_maxlen

        # Ensure group and stream exist
        try:
            self.client.xgroup_create(self.stream_key, self.group_name, id="$", mkstream=True)
            logger.info(f"Created Redis stream '{self.stream_key}' and consumer group '{self.group_name}'")
        except redis.exceptions.ResponseError as e:
            if "BUSYGROUP" not in str(e):
                raise e

    def enqueue(self, job_id: str) -> None:
        self.client.xadd(self.stream_key, {"job_id": job_id}, maxlen=self.maxlen, approximate=True)

    def dequeue(self, consumer_name: Optional[str] = None, exclude_ids: Optional[List[str]] = None) -> Optional[Tuple[str, str]]:
        if not consumer_name:
            consumer_name = f"worker-{socket.gethostname()}-{os.getpid()}"
        if exclude_ids is None:
            exclude_ids = []

        # 1. Try to read pending messages for this consumer (PEL scan)
        start_id = "0-0"
        while True:
            try:
                res = self.client.xreadgroup(
                    groupname=self.group_name,
                    consumername=consumer_name,
                    streams={self.stream_key: start_id},
                    count=1
                )
            except Exception as e:
                logger.error(f"RedisStreamEmbeddingQueue: Failed to read pending: {e}")
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
            res = self.client.xreadgroup(
                groupname=self.group_name,
                consumername=consumer_name,
                streams={self.stream_key: ">"},
                count=1,
                block=2000
            )
        except Exception as e:
            logger.error(f"RedisStreamEmbeddingQueue: Failed to read new: {e}")
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

    def size(self) -> int:
        try:
            return self.client.xlen(self.stream_key)
        except redis.exceptions.RedisError as e:
            logger.error(f"RedisStreamEmbeddingQueue: Failed to get size: {e}")
            return 0

    def ack(self, entry_id: str) -> None:
        # Attempt to clean up retry hash key on successful ACK
        try:
            entries = self.client.xrange(self.stream_key, min=entry_id, max=entry_id, count=1)
            if entries:
                _, data = entries[0]
                job_id = data.get("job_id")
                if job_id:
                    self.client.hdel(self.retry_hash_key, job_id)
        except Exception as e:
            logger.debug(f"RedisStreamEmbeddingQueue: Retry hash cleanup skipped or failed: {e}")

        try:
            self.client.xack(self.stream_key, self.group_name, entry_id)
        except Exception as e:
            logger.error(f"RedisStreamEmbeddingQueue: Failed to XACK entry {entry_id}: {e}")

    def get_dlq_entries(self) -> List[Dict[str, Any]]:
        try:
            entries = self.client.xrange(self.dlq_key, min="-", max="+")
            results = []
            for entry_id, data in entries:
                results.append({
                    "entry_id": entry_id,
                    "job_id": data.get("job_id"),
                    "failed_at": data.get("failed_at"),
                    "original_entry_id": data.get("entry_id")
                })
            return results
        except Exception as e:
            logger.error(f"RedisStreamEmbeddingQueue: Failed to fetch DLQ entries: {e}")
            return []

    @property
    def queue_backend(self) -> str:
        return "redis"


# Global singleton instance selection
embedding_queue = None

if settings.redis_url:
    try:
        logger.info(f"Initializing RedisStreamEmbeddingQueue connecting to {settings.redis_url}")
        embedding_queue = RedisStreamEmbeddingQueue(redis_url=settings.redis_url)
    except Exception as e:
        logger.critical(
            f"CRITICAL: Failed to connect to Redis at {settings.redis_url} for embedding queue. "
            f"Falling back to InMemoryEmbeddingQueue. This process queue is NOT distributed/durable! Error: {e}",
            exc_info=True
        )
        embedding_queue = InMemoryEmbeddingQueue()
else:
    embedding_queue = InMemoryEmbeddingQueue()
