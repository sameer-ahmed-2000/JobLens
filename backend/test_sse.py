import pytest
import os
import sys
import time
import json
import hashlib
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock, PropertyMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Setup test DB (SQLite file-based)
test_engine = create_engine("sqlite:///test_sse.db", connect_args={"check_same_thread": False})
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

# Monkey-patch SessionLocal globally before importing main application to redirect database operations to SQLite
import app.database
app.database.SessionLocal = TestSessionLocal

import app.repositories.uow
app.repositories.uow.SessionLocal = TestSessionLocal

from app.database import Base
from app.repositories.uow import UnitOfWork
from app.services.seeder import seed_if_empty
from app.models.orm import UserORM, JobMatchORM, JobORM, CompanyORM
from app.main import app

class SQLiteUnitOfWork(UnitOfWork):
    def __init__(self):
        super().__init__(session_factory=TestSessionLocal)

# Initialize TestClient
from fastapi.testclient import TestClient
client = TestClient(app)

@pytest.fixture(autouse=True, scope="module")
def setup_database():
    """Create tables and seed database before running module tests."""
    Base.metadata.create_all(bind=test_engine)
    seed_if_empty(uow_factory=SQLiteUnitOfWork)
    yield
    Base.metadata.drop_all(bind=test_engine)
    if os.path.exists("test_sse.db"):
        try:
            os.remove("test_sse.db")
        except Exception:
            pass


def test_sse_ticket_generation_and_consumption():
    """Test generating a short-lived ticket and consuming it via the SSE endpoint."""
    with patch("app.repositories.uow.UnitOfWork", SQLiteUnitOfWork):
        
        # 1. Post without auth header should fail
        res = client.post("/api/stream/ticket")
        assert res.status_code == 401
        
        # 2. Post with correct token should succeed and return ticket
        headers = {"Authorization": "Bearer default-user-token"}
        res = client.post("/api/stream/ticket", headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert "ticket" in data
        ticket = data["ticket"]
        
        # 3. Request SSE stream with invalid ticket should fail
        res_sse_fail = client.get("/api/stream/jobs?ticket=invalid-ticket")
        assert res_sse_fail.status_code == 401
        
        # 4. Request SSE stream with valid ticket should authorize (check mock or client return)
        # Note: StreamingResponse blocks or loops, so we mock aioredis to verify connection setup and ticket consumption.
        with patch("redis.asyncio.from_url") as mock_aioredis_from_url:
            from unittest.mock import AsyncMock
            mock_client = MagicMock()
            mock_client.close = AsyncMock()
            
            mock_pubsub = MagicMock()
            mock_pubsub.subscribe = AsyncMock()
            mock_pubsub.unsubscribe = AsyncMock()
            mock_pubsub.get_message = AsyncMock(side_effect=Exception("Stop stream loop in test"))
            
            mock_client.pubsub.return_value = mock_pubsub
            mock_aioredis_from_url.return_value = mock_client
            
            # Request stream. It should throw the mock exception in event_gen, which gets caught and terminates the stream.
            res_sse = client.get(f"/api/stream/jobs?ticket={ticket}")
            assert res_sse.status_code == 200
            
            # Verifying that the ticket is one-time use and immediately deleted
            res_sse_reuse = client.get(f"/api/stream/jobs?ticket={ticket}")
            assert res_sse_reuse.status_code == 401


def test_matches_backfill_endpoint():
    """Test the /api/matches backfill route with ISO 8601 timestamps."""
    with patch("app.repositories.uow.UnitOfWork", SQLiteUnitOfWork):
        
        headers = {"Authorization": "Bearer default-user-token"}
        
        # Create unique test matches with custom timestamps
        with SQLiteUnitOfWork() as uow:
            user = uow.session.query(UserORM).first()
            user_id = user.id
            
            comp = CompanyORM(name="SSE test Company")
            uow.session.add(comp)
            uow.session.flush()
            
            # Create two test jobs
            job_old = JobORM(title="Old job match", description="Old description", url="https://example.com/old", company_id=comp.id)
            job_new = JobORM(title="New job match", description="New description", url="https://example.com/new", company_id=comp.id)
            uow.session.add(job_old)
            uow.session.add(job_new)
            uow.session.flush()
            
            # Match 1 (Created 10 minutes ago)
            match_old = JobMatchORM(
                user_id=user_id,
                job_id=job_old.id,
                score=0.85,
                created_at=datetime.utcnow() - timedelta(minutes=10)
            )
            # Match 2 (Created 5 seconds ago)
            match_new = JobMatchORM(
                user_id=user_id,
                job_id=job_new.id,
                score=0.92,
                created_at=datetime.utcnow() - timedelta(seconds=5)
            )
            uow.session.add(match_old)
            uow.session.add(match_new)
            uow.commit()
            
        # Get all matches (no since parameter)
        res_all = client.get("/api/matches", headers=headers)
        assert res_all.status_code == 200
        matches_all = res_all.json()
        assert len(matches_all) >= 2
        
        # Filter since 1 minute ago (should only return match_new)
        since_time = (datetime.utcnow() - timedelta(minutes=1)).isoformat() + "Z"
        res_filtered = client.get(f"/api/matches?since={since_time}", headers=headers)
        assert res_filtered.status_code == 200
        matches_filtered = res_filtered.json()
        
        # Should contain the new job, but NOT the old job
        titles = [m["posting"]["title"] for m in matches_filtered]
        assert "New job match" in titles
        assert "Old job match" not in titles


if __name__ == "__main__":
    pytest.main([__file__])
