import os
import sys
import logging
from unittest.mock import patch
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s - %(message)s")
logger = logging.getLogger("test_signup")

from app.database import Base
import app.models.orm
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker
from app.repositories.uow import UnitOfWork
from app.services.seeder import seed_if_empty
from app.main import app

test_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    echo=False
)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

class TestUnitOfWork(UnitOfWork):
    def __init__(self):
        super().__init__(session_factory=TestSessionLocal)

def test_signup_flow():
    logger.info("=== Starting Test: Invite-Gated Self-Serve Signup API ===")
    Base.metadata.create_all(bind=test_engine)
    seed_if_empty(uow_factory=TestUnitOfWork)

    with patch("app.repositories.uow.UnitOfWork", TestUnitOfWork), \
         patch("app.routes.auth.UnitOfWork", TestUnitOfWork):
        client = TestClient(app)

        # 1. Invalid invite code should be rejected with 403 Forbidden
        resp_bad_code = client.post("/api/auth/signup", json={
            "name": "Hacker User",
            "email": "hacker@example.com",
            "invite_code": "wrong-code-123"
        })
        assert resp_bad_code.status_code == 403, f"Expected 403, got {resp_bad_code.status_code}"
        logger.info("Passed: Invalid invite code rejected with 403.")

        # 2. Valid signup should create user & resume, returning raw_token once
        signup_payload = {
            "name": "Jane Mentee",
            "email": "jane@example.com",
            "invite_code": "joblens-beta-2026",
            "whatsapp_number": "+1234567890",
            "title": "Lead AI Architect",
            "years_experience": 5.0,
            "skills": ["Python", "LangGraph", "PyTorch"],
            "projects": [{"name": "Agent System", "description": "Built multi-agent framework"}]
        }
        resp_signup = client.post("/api/auth/signup", json=signup_payload)
        assert resp_signup.status_code == 200, f"Expected 200, got {resp_signup.status_code}: {resp_signup.text}"
        data = resp_signup.json()
        assert "raw_token" in data
        assert data["user"]["email"] == "jane@example.com"
        raw_token = data["raw_token"]
        logger.info("Passed: Valid signup succeeded and returned raw_token.")

        # 3. Duplicate signup with same email should be rejected with 400 Bad Request
        resp_dup = client.post("/api/auth/signup", json=signup_payload)
        assert resp_dup.status_code == 400, f"Expected 400, got {resp_dup.status_code}"
        logger.info("Passed: Duplicate email rejected with 400.")

        # 4. Use returned raw_token to authenticate request against protected /api/profile endpoint
        resp_profile = client.get("/api/profile", headers={
            "Authorization": f"Bearer {raw_token}"
        })
        assert resp_profile.status_code == 200, f"Expected 200, got {resp_profile.status_code}: {resp_profile.text}"
        prof_data = resp_profile.json()
        assert prof_data["email"] == "jane@example.com"
        assert prof_data["name"] == "Jane Mentee"
        logger.info("Passed: Generated raw_token authenticated GET /api/profile successfully!")

    logger.info("=== ALL SIGNUP API TESTS PASSED SUCCESSFULLY! ===")

if __name__ == "__main__":
    try:
        test_signup_flow()
    except Exception as e:
        logger.error(f"Signup test failed: {e}", exc_info=True)
        sys.exit(1)
