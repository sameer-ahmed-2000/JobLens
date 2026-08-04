import os
import pytest
from app.config import Settings, validate_jwt_secret

def test_jwt_enforcement_development():
    # In development mode, default JWT secret should NOT raise RuntimeError
    os.environ["ENVIRONMENT"] = "development"
    os.environ["JWT_SECRET_KEY"] = "super-secret-key-change-me"
    s = Settings()
    # Should complete without error
    validate_jwt_secret(s)

def test_jwt_enforcement_production_fails():
    # In production mode, default JWT secret MUST raise RuntimeError
    os.environ["ENVIRONMENT"] = "production"
    os.environ["JWT_SECRET_KEY"] = "super-secret-key-change-me"
    s = Settings()
    with pytest.raises(RuntimeError) as exc_info:
        validate_jwt_secret(s)
    assert "CRITICAL SECURITY FAILURE" in str(exc_info.value)

def test_expired_jwt_returns_401():
    from datetime import datetime, timedelta, timezone
    import jwt
    from fastapi import HTTPException, status
    from app.config import settings
    from app.routes.auth import get_current_user_id
    from fastapi.security import HTTPAuthorizationCredentials

    # Mint an expired token
    now = datetime.now(timezone.utc)
    expired_time = now - timedelta(days=1)
    payload = {
        "sub": "test-user-id",
        "email": "test@example.com",
        "exp": int(expired_time.timestamp()),
        "iat": int((expired_time - timedelta(minutes=10)).timestamp())
    }
    expired_token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=expired_token)

    with pytest.raises(HTTPException) as exc_info:
        get_current_user_id(creds)

    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert "Token has expired" in exc_info.value.detail

