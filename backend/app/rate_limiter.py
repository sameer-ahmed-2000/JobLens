import hashlib
import logging
from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from app.config import settings

logger = logging.getLogger("rate_limiter")

def get_user_or_ip_key(request: Request) -> str:
    """
    Key function resolving rate limit identity to user_id (via SHA-256 token hash)
    or client IP address if unauthenticated.
    """
    auth_header = request.headers.get("Authorization") or request.headers.get("authorization")
    if auth_header and auth_header.startswith("Bearer "):
        raw_token = auth_header[7:].strip()
        if raw_token:
            return f"user:{hashlib.sha256(raw_token.encode('utf-8')).hexdigest()[:16]}"

    # Fallback to client IP
    return f"ip:{get_remote_address(request)}"

def create_limiter() -> Limiter:
    storage_uri = getattr(settings, "redis_url", None)
    if storage_uri:
        try:
            from app.redis_client import get_redis_client
            client = get_redis_client()
            client.ping()
            logger.info(f"Rate limiter initialized with Redis storage at {storage_uri}")
            return Limiter(key_func=get_user_or_ip_key, storage_uri=storage_uri)
        except Exception as e:
            logger.warning(f"Redis unavailable for rate limiter storage ({e}). Falling back to memory:// storage.")
    
    return Limiter(key_func=get_user_or_ip_key, storage_uri="memory://")


limiter = create_limiter()

