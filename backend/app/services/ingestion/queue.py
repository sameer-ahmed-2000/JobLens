from abc import ABC, abstractmethod
from typing import Optional, List
import collections
import threading

class IEmbeddingQueue(ABC):
    @abstractmethod
    def enqueue(self, job_id: str) -> None:
        pass

    @abstractmethod
    def dequeue(self) -> Optional[str]:
        pass

    @abstractmethod
    def size(self) -> int:
        pass

class InMemoryEmbeddingQueue(IEmbeddingQueue):
    def __init__(self):
        self._queue = collections.deque()
        self._lock = threading.Lock()
        self._set = set()

    def enqueue(self, job_id: str) -> None:
        with self._lock:
            if job_id not in self._set:
                self._queue.append(job_id)
                self._set.add(job_id)

    def dequeue(self) -> Optional[str]:
        with self._lock:
            if not self._queue:
                return None
            job_id = self._queue.popleft()
            self._set.discard(job_id)
            return job_id

    def size(self) -> int:
        with self._lock:
            return len(self._queue)

# Global singleton instance for MVP
embedding_queue = InMemoryEmbeddingQueue()
