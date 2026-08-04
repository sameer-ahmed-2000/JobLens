import uuid
import time
import json
import logging
from typing import Dict
from fastapi import APIRouter, Depends, Query, HTTPException, status, Request
from fastapi.responses import StreamingResponse
import redis.asyncio as aioredis

from app.config import settings
from app.routes.auth import get_current_user_id
from app.rate_limiter import limiter

logger = logging.getLogger(__name__)

router = APIRouter()

# In-memory fallback for SSE tickets when Redis is not running
_fallback_tickets: Dict[str, tuple[str, float]] = {}


@router.post("/stream/ticket")
@limiter.limit("30/minute")
async def create_stream_ticket(request: Request, current_user_id: str = Depends(get_current_user_id)):
    """
    Mints a short-lived, single-purpose one-time ticket for opening the SSE stream.
    Valid for 60 seconds.
    """
    ticket_id = str(uuid.uuid4())

    from app.services.ingestion.queue import embedding_queue
    if hasattr(embedding_queue, "queue_backend") and embedding_queue.queue_backend == "redis":
        try:
            embedding_queue.client.setex(f"sse_ticket:{ticket_id}", 60, current_user_id)
        except Exception as e:
            logger.error(f"Failed to save SSE ticket to Redis: {e}")
            _fallback_tickets[ticket_id] = (current_user_id, time.time() + 60.0)
    else:
        _fallback_tickets[ticket_id] = (current_user_id, time.time() + 60.0)

    return {"ticket": ticket_id}


@router.get("/stream/jobs")
async def stream_jobs(ticket: str = Query(..., description="Short-lived one-time ticket")):
    """
    SSE stream endpoint using a one-time ticket.
    """
    user_id = None

    # 1. Try to retrieve user_id from Redis
    from app.services.ingestion.queue import embedding_queue
    if hasattr(embedding_queue, "queue_backend") and embedding_queue.queue_backend == "redis":
        try:
            redis_key = f"sse_ticket:{ticket}"
            user_id = embedding_queue.client.get(redis_key)
            if user_id:
                embedding_queue.client.delete(redis_key)
        except Exception as e:
            logger.error(f"Failed to read/delete SSE ticket from Redis: {e}")

    # 2. Fallback to in-memory if not found in Redis
    if not user_id:
        if ticket in _fallback_tickets:
            stored_user_id, expiry = _fallback_tickets.pop(ticket)
            if time.time() <= expiry:
                user_id = stored_user_id
                logger.warning("SSE stream authenticated using fallback in-memory ticket (Redis unreachable or disabled).")

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid, expired, or already-used stream ticket."
        )

    async def event_gen():
        from app.redis_client import get_async_redis_client
        client = get_async_redis_client()
        pubsub = client.pubsub()
        await pubsub.subscribe(f"job_events:{user_id}")
        try:
            while True:
                msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=15.0)
                if msg and msg["type"] == "message":
                    yield f"data: {msg['data']}\n\n"
                else:
                    yield ": heartbeat\n\n"
        except Exception as e:
            logger.error(f"SSE stream error: {e}")
        finally:
            await pubsub.unsubscribe()


    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={
            "X-Accel-Buffering": "no",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive"
        }
    )
