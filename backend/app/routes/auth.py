import hashlib
import logging
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.repositories.uow import UnitOfWork

logger = logging.getLogger("auth")

security = HTTPBearer()

def get_current_user_id(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """
    HTTPBearer dependency resolving the client token to a user ID.
    Hashes the incoming raw token with SHA-256 and queries the database token_hash.
    """
    token = credentials.credentials
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token is missing."
        )

    # Compute SHA-256 hash of the token
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()

    with UnitOfWork() as uow:
        user = uow.users.get_by_token_hash(token_hash)
        if user:
            return user["id"]

    logger.warning(f"Failed authentication attempt with token hash: {token_hash}")
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication token."
    )
