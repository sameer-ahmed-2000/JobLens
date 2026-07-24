import os
import sys
import logging
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s - %(message)s")
logger = logging.getLogger("test_signup")

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.database import Base
import app.models.orm
from app.repositories.uow import UnitOfWork
from app.main import app
from app.config import settings


from sqlalchemy.pool import StaticPool
test_engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool, echo=False)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


class TestUnitOfWork(UnitOfWork):
    def __init__(self):
        super().__init__(session_factory=TestSessionLocal)

def test_self_serve_signup():
    logger.info("=== Starting Test: Self-Serve Signup ===")
    Base.metadata.create_all(bind=test_engine)

    def mock_uow_init(self, session_factory=None):
        self.session_factory = TestSessionLocal
        self.session = None

    with patch.object(UnitOfWork, "__init__", mock_uow_init), \
         patch("app.services.embeddings.embedding_service.embed_resume_section", return_value=[0.1] * 384):






        client = TestClient(app)

        # 1. Invalid invite code -> 403
        resp = client.post("/api/auth/signup", json={
            "name": "Jane Doe",
            "email": "jane@example.com",
            "invite_code": "wrong-code"
        })
        assert resp.status_code == 403, f"Expected 403 for wrong invite code, got {resp.status_code}"
        logger.info("Passed: Invalid invite code correctly rejected with 403.")

        # 2. Valid signup -> 200
        valid_invite = settings.signup_invite_token
        signup_payload = {
            "name": "Jane Doe",
            "email": "jane@example.com",
            "invite_code": valid_invite,
            "whatsapp_number": "+15551234567",
            "title": "Senior AI Architect",
            "years_experience": 5.0,
            "skills": ["Python", "FastAPI", "LangChain"],
            "projects": [{"name": "RAG Bot", "description": "built RAG", "technologies": ["Python"]}]
        }
        resp = client.post("/api/auth/signup", json=signup_payload)
        assert resp.status_code == 200, f"Expected 200 for valid signup, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert "raw_token" in data
        assert data["user"]["email"] == "jane@example.com"
        raw_token = data["raw_token"]
        logger.info(f"Passed: Signup succeeded! Received raw_token: {raw_token[:8]}...")

        # 3. Duplicate email -> 400
        resp_dup = client.post("/api/auth/signup", json=signup_payload)
        assert resp_dup.status_code == 400, f"Expected 400 for duplicate email, got {resp_dup.status_code}"
        logger.info("Passed: Duplicate email registration correctly rejected with 400.")

        # 4. Access protected endpoint using newly issued raw_token -> 200
        headers = {"Authorization": f"Bearer {raw_token}"}
        resp_prof = client.get("/api/profile", headers=headers)
        assert resp_prof.status_code == 200, f"Expected 200 for authenticated profile request, got {resp_prof.status_code}: {resp_prof.text}"
        prof_data = resp_prof.json()
        assert prof_data["email"] == "jane@example.com"
        assert prof_data["name"] == "Jane Doe"
        logger.info("Passed: Authenticated request using newly generated raw_token resolved user profile successfully!")

    logger.info("=== ALL SELF-SERVE SIGNUP TESTS PASSED SUCCESSFULLY! ===")

if __name__ == "__main__":
    try:
        test_self_serve_signup()
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        sys.exit(1)
