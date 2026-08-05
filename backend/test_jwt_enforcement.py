import os
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta, timezone
import jwt
from fastapi import HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
import redis

from app.config import Settings, validate_jwt_secret, settings
from app.routes.auth import (
    create_jwt_token, revoke_jti, is_jti_revoked,
    get_current_user_payload, get_current_user_id, signout
)
from app.routes.api import rotate_token, TokenRotateConfirm

TEST_SECRET = "super-secret-key-that-is-at-least-32-chars-long"

def test_jwt_enforcement_default_fails_unconditionally():
    # Default/insecure JWT secret MUST raise RuntimeError regardless of environment
    os.environ["ENVIRONMENT"] = "development"
    os.environ["JWT_SECRET_KEY"] = "super-secret-key-change-me"
    s = Settings()
    with pytest.raises(RuntimeError) as exc_info:
        validate_jwt_secret(s)
    assert "CRITICAL SECURITY FAILURE" in str(exc_info.value)

def test_jwt_enforcement_missing_fails_unconditionally():
    os.environ["ENVIRONMENT"] = "production"
    os.environ["JWT_SECRET_KEY"] = ""
    s = Settings()
    with pytest.raises(RuntimeError) as exc_info:
        validate_jwt_secret(s)
    assert "CRITICAL SECURITY FAILURE" in str(exc_info.value)

def test_expired_jwt_returns_401():
    now = datetime.now(timezone.utc)
    expired_time = now - timedelta(days=1)
    payload = {
        "sub": "test-user-id",
        "email": "test@example.com",
        "jti": "test-jti-expired",
        "exp": int(expired_time.timestamp()),
        "iat": int((expired_time - timedelta(minutes=10)).timestamp())
    }
    secret = settings.jwt_secret_key or TEST_SECRET
    expired_token = jwt.encode(payload, secret, algorithm=settings.jwt_algorithm)
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=expired_token)

    with patch("app.routes.auth.settings.jwt_secret_key", secret):
        with pytest.raises(HTTPException) as exc_info:
            get_current_user_payload(creds)

    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert "Token has expired" in exc_info.value.detail

def test_is_jti_revoked_key_absent_returns_false():
    mock_redis = MagicMock()
    mock_redis.exists.return_value = 0
    with patch("app.redis_client.get_redis_client", return_value=mock_redis):
        assert is_jti_revoked("clean-jti-uuid") is False

def test_is_jti_revoked_redis_error_fails_closed():
    mock_redis = MagicMock()
    mock_redis.exists.side_effect = redis.ConnectionError("Redis cluster unreachable")
    with patch("app.redis_client.get_redis_client", return_value=mock_redis):
        with pytest.raises(HTTPException) as exc_info:
            is_jti_revoked("any-jti")
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "unable to verify token revocation status" in exc_info.value.detail

def test_signout_revokes_token():
    mock_redis = MagicMock()
    now_ts = int(datetime.now(timezone.utc).timestamp())
    exp_ts = now_ts + 3600

    payload = {
        "user_id": "user-123",
        "sub": "user-123",
        "jti": "jti-to-revoke-123",
        "exp": exp_ts,
        "email": "test@example.com"
    }

    with patch("app.redis_client.get_redis_client", return_value=mock_redis):
        res = signout(payload)
        assert res["message"] == "Successfully signed out. Token invalidated."
        mock_redis.setex.assert_called_once()
        args = mock_redis.setex.call_args[0]
        assert args[0] == "revoked_jti:jti-to-revoke-123"

def test_rotate_token_revokes_old_jwt_and_mints_new():
    mock_redis = MagicMock()
    now_ts = int(datetime.now(timezone.utc).timestamp())
    exp_ts = now_ts + 3600

    payload = {
        "user_id": "user-123",
        "sub": "user-123",
        "jti": "jti-old-token-456",
        "exp": exp_ts,
        "email": "test@example.com"
    }
    body = TokenRotateConfirm(confirm=True)

    secret = settings.jwt_secret_key or TEST_SECRET
    with patch("app.redis_client.get_redis_client", return_value=mock_redis), \
         patch("app.routes.auth.settings.jwt_secret_key", secret), \
         patch("app.repositories.uow.UnitOfWork") as mock_uow_class:

        mock_uow = MagicMock()
        mock_uow.users.update_token_hash.return_value = True
        mock_uow_class.return_value.__enter__.return_value = mock_uow

        res = rotate_token(body=body, payload=payload)
        assert "new_token" in res
        assert res["new_token"] != payload["jti"]
        mock_redis.setex.assert_called_once()
        assert mock_redis.setex.call_args[0][0] == "revoked_jti:jti-old-token-456"


