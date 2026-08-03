import os
import sys
import logging
from unittest.mock import patch
import bcrypt

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s - %(message)s")
logger = logging.getLogger("test_auth")

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

def test_auth_flows():
    logger.info("=== Starting Test: Auth Flows ===")
    Base.metadata.create_all(bind=test_engine)

    def mock_uow_init(self, session_factory=None):
        self.session_factory = TestSessionLocal
        self.session = None

    with patch.object(UnitOfWork, "__init__", mock_uow_init), \
         patch("app.services.embeddings.embedding_service.embed_resume_section", return_value=[0.1] * 384):

        client = TestClient(app)

        # Pre-seed a user with NULL hashed_password to test dummy hash path
        with UnitOfWork() as uow:
            uow.users.create(
                user_id="default-user-id",
                name="Demo User",
                email="demo@example.com",
                whatsapp_number=None,
                token_hash="demo_token_hash",
                hashed_password=None
            )
            uow.commit()

        # 1. Test Demo User with NULL password signin -> 401 Unauthorized (not 500)
        resp = client.post("/api/auth/signin", json={
            "email": "demo@example.com",
            "password": "anypassword123"
        })
        assert resp.status_code == 401, f"Expected 401 for NULL password user, got {resp.status_code}"
        logger.info("Passed: Dummy hash guard works cleanly for NULL password user.")

        # 2. Invalid signup missing password -> 422
        resp = client.post("/api/auth/signup", json={
            "name": "Jane Doe",
            "email": "jane@example.com",
            "invite_code": settings.signup_invite_token
        })
        assert resp.status_code == 422, "Expected 422 for missing password"

        # 3. Valid signup -> 200
        valid_invite = settings.signup_invite_token
        signup_payload = {
            "name": "Jane Doe",
            "email": "jane@example.com",
            "password": "strongpassword123",
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
        logger.info("Passed: Signup succeeded!")

        # 4. Valid Signin -> 200
        signin_payload = {
            "email": "jane@example.com",
            "password": "strongpassword123"
        }
        resp_signin = client.post("/api/auth/signin", json=signin_payload)
        assert resp_signin.status_code == 200, f"Expected 200 for valid signin, got {resp_signin.status_code}"
        signin_data = resp_signin.json()
        assert "raw_token" in signin_data
        logger.info("Passed: Signin succeeded with valid credentials.")

        # 5. Invalid Signin -> 401
        invalid_signin = {
            "email": "jane@example.com",
            "password": "wrongpassword"
        }
        resp_invalid = client.post("/api/auth/signin", json=invalid_signin)
        assert resp_invalid.status_code == 401, f"Expected 401 for invalid signin, got {resp_invalid.status_code}"
        logger.info("Passed: Signin failed with invalid credentials.")

        # 6. Signup with Non-ASCII password round-trip -> 200
        non_ascii_payload = {**signup_payload, "email": "emoji@example.com", "password": "pass😎word123"}
        resp_emoji_signup = client.post("/api/auth/signup", json=non_ascii_payload)
        assert resp_emoji_signup.status_code == 200, f"Expected 200 for emoji signup, got {resp_emoji_signup.status_code}"
        
        resp_emoji_signin = client.post("/api/auth/signin", json={
            "email": "emoji@example.com",
            "password": "pass😎word123"
        })
        assert resp_emoji_signin.status_code == 200, f"Expected 200 for emoji signin, got {resp_emoji_signin.status_code}"
        logger.info("Passed: Non-ASCII password signup/signin round-trips correctly.")

        # 7. Signup with password exceeding 72 bytes -> 422
        # 'a' is 1 byte, '😎' is 4 bytes. 20 emojis = 80 bytes. Length is 20 chars, which passes string length limits but fails byte length limit.
        long_byte_password = "😎" * 20
        too_long_payload = {**signup_payload, "email": "long@example.com", "password": long_byte_password}
        resp_too_long = client.post("/api/auth/signup", json=too_long_payload)
        assert resp_too_long.status_code == 422, f"Expected 422 for password > 72 bytes, got {resp_too_long.status_code}"
        logger.info("Passed: Password exceeding 72 bytes correctly rejected by Pydantic validator.")

    logger.info("=== ALL AUTH TESTS PASSED SUCCESSFULLY! ===")

if __name__ == "__main__":
    try:
        test_auth_flows()
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        sys.exit(1)
