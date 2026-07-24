import os
import sys
import logging
from unittest.mock import patch, MagicMock
from datetime import datetime, time as dtime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("test_notifications")

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.database import Base
from app.models.orm import UserORM, JobMatchORM, JobORM, CompanyORM
from app.repositories.uow import UnitOfWork
from app.main import app
from app.notifier import is_in_quiet_hours

test_engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool, echo=False)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

def test_quiet_hours_logic():
    logger.info("=== Starting Test: Quiet Hours Functionality ===")
    
    # 1. Test None inputs
    assert not is_in_quiet_hours(None, "08:00", "UTC")
    assert not is_in_quiet_hours("22:00", None, "UTC")

    # 2. Test overnight window (22:00 to 08:00) at 23:30 local time -> Should be True
    with patch("zoneinfo.ZoneInfo"):
        with patch("datetime.datetime") as mock_dt:
            # Mock current local time at 23:30
            mock_dt.now.return_value.time.return_value = dtime(23, 30)
            assert is_in_quiet_hours("22:00", "08:00", "UTC") is True

            # Mock current local time at 14:00 -> Should be False
            mock_dt.now.return_value.time.return_value = dtime(14, 0)
            assert is_in_quiet_hours("22:00", "08:00", "UTC") is False

    logger.info("Passed: Quiet hours logic accurately evaluates daytime and overnight windows!")


def test_notification_history_and_profile():
    logger.info("=== Starting Test: Notification History API & Profile Quiet Hours ===")
    Base.metadata.create_all(bind=test_engine)

    class TestUOW(UnitOfWork):
        def __init__(self):
            super().__init__(session_factory=TestSessionLocal)

    def mock_uow_init(self, session_factory=None):
        self.session_factory = TestSessionLocal
        self.session = None

    # Seed test user and matches
    with TestSessionLocal() as session:
        session.query(JobMatchORM).delete()
        session.query(JobORM).delete()
        session.query(CompanyORM).delete()
        session.query(UserORM).delete()

        user = UserORM(
            id="user-123",
            name="Alice Candidate",
            email="alice@example.com",
            notify_threshold=0.80,
            display_threshold=0.70,
            token_hash="4c5dc9b7708905f77f5e5d16316b5dfb425e68cb326dcd55a860e90a7707031e",  # sha256("test-token")
            quiet_hours_start="22:00",
            quiet_hours_end="08:00",
            timezone="Asia/Kolkata"
        )
        session.add(user)

        comp = CompanyORM(id="comp-1", name="Acme Corp", website="https://acme.com")
        session.add(comp)

        job1 = JobORM(id="job-1", company_id="comp-1", title="Senior Backend Engineer", url="https://acme.com/jobs/1", description="Python FastAPI")
        job2 = JobORM(id="job-2", company_id="comp-1", title="Frontend Developer", url="https://acme.com/jobs/2", description="React TypeScript")
        session.add_all([job1, job2])

        # High match >= 0.80 (should show in notification history)
        match1 = JobMatchORM(id="match-1", user_id="user-123", job_id="job-1", score=0.92, rationale="Great Python experience")
        # Low match < 0.80 (should NOT show in notification history)
        match2 = JobMatchORM(id="match-2", user_id="user-123", job_id="job-2", score=0.75, rationale="Missing React experience")
        session.add_all([match1, match2])
        session.commit()

    with patch.object(UnitOfWork, "__init__", mock_uow_init), \
         patch("app.routes.api.get_current_user_id", return_value="user-123"):


        client = TestClient(app)
        headers = {"Authorization": "Bearer test-token"}

        # 1. Get Notification History
        resp = client.get("/api/notifications", headers=headers)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        notifications = resp.json()
        assert len(notifications) == 1, f"Expected 1 notification above 0.80 threshold, got {len(notifications)}"
        assert notifications[0]["title"] == "Senior Backend Engineer"
        assert notifications[0]["company"] == "Acme Corp"
        assert notifications[0]["score"] == 0.92

        logger.info("Passed: GET /api/notifications correctly filters matches above user notify threshold!")

        # 2. Update Profile Quiet Hours & Timezone
        update_payload = {
            "quiet_hours_start": "23:00",
            "quiet_hours_end": "07:00",
            "timezone": "America/New_York"
        }
        resp = client.put("/api/profile", json=update_payload, headers=headers)
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        updated_profile = resp.json()
        assert updated_profile["quiet_hours_start"] == "23:00"
        assert updated_profile["quiet_hours_end"] == "07:00"
        assert updated_profile["timezone"] == "America/New_York"

        logger.info("Passed: PUT /api/profile successfully updated quiet hours and timezone settings!")

if __name__ == "__main__":
    try:
        test_quiet_hours_logic()
        test_notification_history_and_profile()
        logger.info("=== ALL TESTS FOR ITEMS 10 & 11 PASSED SUCCESSFULLY! ===")
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        sys.exit(1)
