import os
import sys
import time
from unittest.mock import MagicMock, patch, ANY

# Ensure backend directory is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.ingestion.queue import RedisStreamEmbeddingQueue
from app.services.ingestion.embedding_worker import EmbeddingWorker

def test_redis_queue_operations():
    print("=== Starting Test: RedisStreamEmbeddingQueue Operations ===")
    
    # Mock redis client
    mock_client = MagicMock()
    mock_client.xgroup_create.return_value = True
    mock_client.xlen.return_value = 5
    
    with patch("redis.Redis.from_url", return_value=mock_client):
        # Initialize
        queue = RedisStreamEmbeddingQueue(redis_url="redis://dummy:6379/0")
        
        # Test queue_backend
        assert queue.queue_backend == "redis"
        
        # Test size
        assert queue.size() == 5
        mock_client.xlen.assert_called_with("jobs:embedding:stream")
        
        # Test enqueue
        queue.enqueue("job-abc")
        mock_client.xadd.assert_called_with(
            "jobs:embedding:stream",
            {"job_id": "job-abc"},
            maxlen=10000,
            approximate=True
        )
        
        # Test dequeue (new message path)
        mock_client.xreadgroup.side_effect = [
            [], # First call: no pending entries
            [("jobs:embedding:stream", [("12345-0", {"job_id": "job-new"})])] # Second call: new entries
        ]
        
        res = queue.dequeue(consumer_name="test-worker")
        assert res is not None
        entry_id, job_id = res
        assert entry_id == "12345-0"
        assert job_id == "job-new"
        
        # Test ack
        mock_client.xrange.return_value = [("12345-0", {"job_id": "job-new"})]
        queue.ack("12345-0")
        mock_client.hdel.assert_called_with("jobs:embedding:retries", "job-new")
        mock_client.xack.assert_called_with("jobs:embedding:stream", "embedding_workers", "12345-0")

        # Test get_dlq_entries
        mock_client.xrange.return_value = [
            ("dlq-1", {"job_id": "job-failed", "failed_at": "123.45", "entry_id": "12345-0"})
        ]
        dlq_entries = queue.get_dlq_entries()
        assert len(dlq_entries) == 1
        assert dlq_entries[0]["job_id"] == "job-failed"
        assert dlq_entries[0]["failed_at"] == "123.45"
        
    print("=== RedisStreamEmbeddingQueue Operations Test Passed! ===\n")

def test_worker_watchdog_and_retry_exclusions():
    print("=== Starting Test: Worker Watchdog and Retry Exclusions ===")
    
    mock_client = MagicMock()
    mock_client.xgroup_create.return_value = True
    
    with patch("redis.Redis.from_url", return_value=mock_client):
        queue = RedisStreamEmbeddingQueue(redis_url="redis://dummy:6379/0")
        
        # Initialize worker
        worker = EmbeddingWorker(queue=queue)
        worker.consumer_name = "test-worker"
        
        # 1. Test process_once exclusions
        # Dequeue mocks: first call returns a job, second call returns None
        mock_client.xreadgroup.side_effect = [
            [], # PEL scan returns nothing
            [("jobs:embedding:stream", [("entry-1", {"job_id": "job-1"})])], # new read returns entry-1
            [], # Second PEL scan returns nothing
            [] # Second new read returns nothing
        ]
        
        # Mock process_job_by_id to fail (returns False)
        with patch.object(worker, "process_job_by_id", return_value=False):
            processed = worker.process_once(max_batch=2)
            assert processed == 0
            # Since processing failed, entry-1 should be in worker's failed list
            assert "entry-1" in worker._failed_entries
            
        # The next dequeue should pass entry-1 in exclude_ids
        mock_client.xreadgroup.reset_mock()
        mock_client.xreadgroup.side_effect = [
            [("jobs:embedding:stream", [("entry-1", {"job_id": "job-1"})])], # first PEL scan returns entry-1 (which we exclude)
            [], # second PEL scan (after scanning past entry-1) returns nothing
            []  # new read returns nothing
        ]
        worker.process_once(max_batch=1)
        
        # Check call arguments
        called_args = mock_client.xreadgroup.call_args_list
        assert len(called_args) == 3
        # First call streams parameter
        assert called_args[0][1]["streams"] == {"jobs:embedding:stream": "0-0"}
        # Second call streams parameter (scanned past entry-1)
        assert called_args[1][1]["streams"] == {"jobs:embedding:stream": "entry-1"}
        # Third call streams parameter
        assert called_args[2][1]["streams"] == {"jobs:embedding:stream": ">"}
        
        # 2. Test Watchdog recovery loop
        # Mock xautoclaim returning a claimed entry
        mock_client.xautoclaim.return_value = (
            "entry-2", # next_start_id
            [("entry-2", {"job_id": "job-stuck"})], # claimed_entries
            []
        )
        
        # Try count is 1 (not exceeded max retries)
        mock_client.hincrby.return_value = 1
        
        mock_client.xadd.reset_mock()
        mock_client.xack.reset_mock()
        
        worker._running = True
        worker.recover_stuck_jobs()
        
        mock_client.hincrby.assert_called_with("jobs:embedding:retries", "job-stuck", 1)
        # Should NOT have DLQed or ACKed yet
        mock_client.xadd.assert_not_called()
        mock_client.xack.assert_not_called()
        
        # Try count is 4 (exceeded max retries=3)
        mock_client.hincrby.return_value = 4
        mock_client.xrange.return_value = [("entry-2", {"job_id": "job-stuck"})]
        
        worker.recover_stuck_jobs()
        # Should have DLQed, and then ACKed (through ack())
        mock_client.xadd.assert_called_with(
            "jobs:embedding:dlq",
            {
                "job_id": "job-stuck",
                "entry_id": "entry-2",
                "failed_at": ANY,
                "reason": "Max retries exceeded"
            }
        )
        mock_client.xack.assert_called_with("jobs:embedding:stream", "embedding_workers", "entry-2")
        
    print("=== Worker Watchdog and Retry Exclusions Test Passed! ===\n")

if __name__ == "__main__":
    try:
        test_redis_queue_operations()
        test_worker_watchdog_and_retry_exclusions()
        print("=== ALL REDIS INTEGRATION TESTS PASSED SUCCESSFULLY! ===")
    except Exception as e:
        import traceback
        traceback.print_exc()
        sys.exit(1)
