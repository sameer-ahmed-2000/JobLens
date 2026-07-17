import os
import sys
import json
import uuid
from unittest.mock import MagicMock, patch
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Ensure backend directory is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ── Test DB (SQLite, file-based) ─────────────────────────────────────────────
test_engine = create_engine(
    "sqlite:///test_notifier.db",
    connect_args={"check_same_thread": False},
)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

# Monkey-patch BEFORE any app modules are imported
import app.database
app.database.SessionLocal = TestSessionLocal

import app.repositories.uow
app.repositories.uow.SessionLocal = TestSessionLocal

from app.database import Base
from app.repositories.uow import UnitOfWork
from app.services.seeder import seed_if_empty
from app.models.orm import UserORM, JobMatchORM, JobORM, CompanyORM
from app.notifier import Notifier
from app.main import app
from fastapi.testclient import TestClient


class SQLiteUnitOfWork(UnitOfWork):
    def __init__(self):
        super().__init__(session_factory=TestSessionLocal)


# ── Module-scoped fixture: tables + seed + notifier users/jobs/matches ───────
@pytest.fixture(autouse=True, scope="module")
def setup_database():
    """
    Create all tables and seed once per test-module run.
    Notifier-specific users, jobs, and matches are also inserted here so that
    _build_notifier_with_fixtures() is never called more than once, avoiding
    UNIQUE constraint violations on jobs.url across repeated test functions.
    """
    Base.metadata.create_all(bind=test_engine)
    seed_if_empty(uow_factory=SQLiteUnitOfWork)

    # Insert notifier-specific fixtures ONCE at module scope
    with SQLiteUnitOfWork() as uow:
        uow.users.create(
            name="WA User", email="wa@notifier.test",
            user_id="user-wa", whatsapp_number="+1999999999",
            notify_threshold=0.80, display_threshold=0.70,
        )
        uow.users.create(
            name="Email User", email="email@notifier.test",
            user_id="user-email", whatsapp_number=None,
            notify_threshold=0.85, display_threshold=0.75,
        )

        comp = CompanyORM(name="Notifier Corp")
        uow.session.add(comp)
        uow.session.flush()

        # Use UUID-suffixed URLs so they never collide with the seeder data
        run_id = uuid.uuid4().hex[:8]
        job_wa  = JobORM(title="AI Lead 1", description="desc", url=f"https://ex.com/j1-{run_id}", company_id=comp.id)
        job_em  = JobORM(title="AI Lead 2", description="desc", url=f"https://ex.com/j2-{run_id}", company_id=comp.id)
        job_low = JobORM(title="AI Lead 3", description="desc", url=f"https://ex.com/j3-{run_id}", company_id=comp.id)
        uow.session.add_all([job_wa, job_em, job_low])
        uow.session.flush()

        uow.session.add(JobMatchORM(id="match-wa-1",    user_id="user-wa",    job_id=job_wa.id,  score=0.82, rationale="Matches skills"))
        uow.session.add(JobMatchORM(id="match-email-1", user_id="user-email", job_id=job_em.id,  score=0.88, rationale="Great match"))
        uow.session.add(JobMatchORM(id="match-low-1",   user_id="user-wa",    job_id=job_low.id, score=0.75, rationale="Low fit"))
        uow.commit()

    yield

    Base.metadata.drop_all(bind=test_engine)
    try:
        os.remove("test_notifier.db")
    except Exception:
        pass


# TestClient initialised at module level; tables already exist by the time
# setup_database's body runs (module fixture runs before any test body).
client = TestClient(app)
AUTH_HEADERS = {"Authorization": "Bearer default-user-token"}


# ── Helper: build a fresh Notifier with mocked Redis and send methods ─────────
def _make_notifier():
    notifier = Notifier()
    mock_redis = MagicMock()
    notifier.redis_client = mock_redis
    notifier.send_whatsapp = MagicMock(return_value=True)
    notifier.send_email    = MagicMock(return_value=True)
    return notifier, mock_redis


# ── Profile endpoint tests ────────────────────────────────────────────────────

def test_profile_get():
    """GET /api/profile returns current user profile."""
    with patch("app.repositories.uow.UnitOfWork", SQLiteUnitOfWork):
        res = client.get("/api/profile", headers=AUTH_HEADERS)
    assert res.status_code == 200, res.text
    profile = res.json()
    assert profile["id"] == "default-user-id"
    assert "notify_threshold" in profile
    assert "display_threshold" in profile


def test_profile_put_valid():
    """PUT /api/profile with notify >= display succeeds."""
    with patch("app.repositories.uow.UnitOfWork", SQLiteUnitOfWork):
        res = client.put("/api/profile", json={
            "name": "Updated Name",
            "email": "user@joblens.ai",
            "whatsapp_number": "+1234567890",
            "notify_threshold": 0.80,
            "display_threshold": 0.75,
        }, headers=AUTH_HEADERS)
    assert res.status_code == 200, res.text
    updated = res.json()
    assert updated["name"] == "Updated Name"
    assert updated["whatsapp_number"] == "+1234567890"
    assert updated["notify_threshold"] == 0.80
    assert updated["display_threshold"] == 0.75


def test_profile_put_invalid_threshold():
    """PUT /api/profile rejects notify_threshold < display_threshold with 400."""
    with patch("app.repositories.uow.UnitOfWork", SQLiteUnitOfWork):
        res = client.put("/api/profile", json={
            "notify_threshold": 0.60,
            "display_threshold": 0.75,
        }, headers=AUTH_HEADERS)
    assert res.status_code == 400, res.text
    assert "cannot be lower than display threshold" in res.json()["detail"]


def test_profile_put_clears_whatsapp():
    """PUT /api/profile with whatsapp_number=None clears the number."""
    with patch("app.repositories.uow.UnitOfWork", SQLiteUnitOfWork):
        res = client.put("/api/profile", json={
            "name": "Demo User",
            "email": "user@joblens.ai",
            "whatsapp_number": None,
            "notify_threshold": 0.85,
            "display_threshold": 0.70,
        }, headers=AUTH_HEADERS)
    assert res.status_code == 200, res.text
    assert res.json()["whatsapp_number"] is None


# ── Notifier logic tests ──────────────────────────────────────────────────────

def _msg(channel_user: str, match_id: str, title: str, score: float, url: str) -> dict:
    return {
        "channel": f"job_events:{channel_user}",
        "data": json.dumps({
            "type": "new_match",
            "job_match_id": match_id,
            "title": title,
            "company": "Notifier Corp",
            "score": score,
            "url": url,
        }),
    }


def test_notifier_below_threshold_skips():
    """Score below notify_threshold (0.75 < 0.80): dedup/rate-limit/send all skipped."""
    notifier, mock_redis = _make_notifier()
    with patch("app.notifier.UnitOfWork", SQLiteUnitOfWork):
        notifier.process_message(_msg("user-wa", "match-low-1", "AI Lead 3", 0.75, "https://ex.com/j3"))

    mock_redis.sadd.assert_not_called()
    mock_redis.incr.assert_not_called()
    notifier.send_whatsapp.assert_not_called()
    notifier.send_email.assert_not_called()


def test_notifier_whatsapp_dispatch_and_dedup_first():
    """
    Score above notify_threshold for WhatsApp user:
    - SADD (dedup) fires BEFORE INCR (rate limit).
    - WhatsApp used; email skipped.
    - Deep link URL embedded in message body.
    """
    notifier, mock_redis = _make_notifier()
    mock_redis.sadd.return_value = 1  # new — not a duplicate
    mock_redis.incr.return_value = 1  # first notification this hour

    with patch("app.notifier.UnitOfWork", SQLiteUnitOfWork):
        notifier.process_message(_msg("user-wa", "match-wa-1", "AI Lead 1", 0.82, "https://ex.com/j1"))

    # Dedup must precede rate-limit check
    calls = mock_redis.method_calls
    sadd_pos = next(i for i, c in enumerate(calls) if c[0] == "sadd")
    incr_pos  = next(i for i, c in enumerate(calls) if c[0] == "incr")
    assert sadd_pos < incr_pos, "SADD (dedup) must be called before INCR (rate limit)"

    mock_redis.sadd.assert_called_with("notified:user-wa", "match-wa-1")
    mock_redis.incr.assert_called_with("notify:rate:user-wa")
    notifier.send_whatsapp.assert_called_once()
    body = notifier.send_whatsapp.call_args[0][1]
    assert "match-wa-1" in body
    assert "http://localhost:5173/?match=match-wa-1" in body
    notifier.send_email.assert_not_called()


def test_notifier_duplicate_skips_rate_limit():
    """Duplicate pub/sub delivery: SADD returns 0 → INCR and send are both skipped."""
    notifier, mock_redis = _make_notifier()
    mock_redis.sadd.return_value = 0  # already in the set — duplicate

    with patch("app.notifier.UnitOfWork", SQLiteUnitOfWork):
        notifier.process_message(_msg("user-wa", "match-wa-1", "AI Lead 1", 0.82, "https://ex.com/j1"))

    mock_redis.sadd.assert_called_with("notified:user-wa", "match-wa-1")
    mock_redis.incr.assert_not_called()          # rate budget preserved
    notifier.send_whatsapp.assert_not_called()
    notifier.send_email.assert_not_called()


def test_notifier_email_fallback():
    """User without WhatsApp falls back to SMTP. Deep link present in email body."""
    notifier, mock_redis = _make_notifier()
    mock_redis.sadd.return_value = 1
    mock_redis.incr.return_value = 1

    with patch("app.notifier.UnitOfWork", SQLiteUnitOfWork):
        notifier.process_message(_msg("user-email", "match-email-1", "AI Lead 2", 0.88, "https://ex.com/j2"))

    notifier.send_whatsapp.assert_not_called()
    notifier.send_email.assert_called_once()
    body = notifier.send_email.call_args[0][2]
    assert "match-email-1" in body
    assert "http://localhost:5173/?match=match-email-1" in body


def test_notifier_rate_limit_exceeded():
    """Rate limit exceeded (INCR returns 6 > cap of 5): send is skipped."""
    notifier, mock_redis = _make_notifier()
    mock_redis.sadd.return_value = 1  # new dedup entry
    mock_redis.incr.return_value = 6  # exceeded cap

    with patch("app.notifier.UnitOfWork", SQLiteUnitOfWork):
        notifier.process_message(_msg("user-email", "match-email-1", "AI Lead 2", 0.88, "https://ex.com/j2"))

    mock_redis.sadd.assert_called_with("notified:user-email", "match-email-1")
    mock_redis.incr.assert_called_with("notify:rate:user-email")
    notifier.send_email.assert_not_called()
    notifier.send_whatsapp.assert_not_called()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
