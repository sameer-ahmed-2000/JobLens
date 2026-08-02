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
