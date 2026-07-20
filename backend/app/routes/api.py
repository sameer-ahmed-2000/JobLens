from fastapi import APIRouter, Depends, Query, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import json
import os
import uuid
import time
from datetime import datetime
import redis.asyncio as aioredis
from app.config import settings
from app.models.schemas import ScoredPosting, GapReportRequest, GapReport, RawPosting, UserProfileSchema, UserProfileUpdateSchema
from app.routes.auth import get_current_user_id

router = APIRouter()

# Load mock data for phase 1
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")

from app.services.discovery_service import discovery_service
from app.services.gap_service import gap_service

@router.get("/postings", response_model=List[ScoredPosting])
async def get_postings(current_user_id: str = Depends(get_current_user_id)):
    """
    Returns a list of job postings, scored and ranked against the user's resume using LangGraph.
    """
    return await discovery_service.get_ranked_postings(user_id=current_user_id, force_refresh=False)

@router.post("/discover", response_model=List[ScoredPosting])
async def trigger_discovery(force_live_search: bool = False, current_user_id: str = Depends(get_current_user_id)):
    """
    Triggers the discovery pipeline: first runs a resume-driven real-time
    search against aggregator sources (Adzuna/Remotive/Arbeitnow) using
    keywords derived from the active resume, then scores and ranks the
    combined pool (ATS boards + live aggregator results) via LangGraph.

    `force_live_search=true` bypasses the debounce window (useful for a
    manual "search now" button in the UI).
    """
    from app.services.resume_index import resume_index
    from app.services.job_scheduler import job_scheduler

    keywords = resume_index.get_search_keywords(user_id=current_user_id)
    if keywords:
        job_scheduler.trigger_live_search(keywords=keywords, force=force_live_search)

    return await discovery_service.get_ranked_postings(user_id=current_user_id, force_refresh=True)


@router.get("/matches/{match_id}", response_model=ScoredPosting)
async def get_match_detail(match_id: str, current_user_id: str = Depends(get_current_user_id)):
    """
    Get job match detail. If fit_rationale is missing/empty in the database,
    triggers lazy rationale generation via LLM and caches the result.
    Enforces ownership check (must belong to current_user_id) and returns 404 on mismatch.
    """
    from app.repositories.uow import UnitOfWork
    from app.models.orm import JobMatchORM, JobORM
    from app.services.llm_router import llm_router
    from fastapi import HTTPException
    
    with UnitOfWork() as uow:
        # Query by match ID and ensure it belongs to the current user
        match = uow.session.query(JobMatchORM).filter(
            JobMatchORM.id == match_id,
            JobMatchORM.user_id == current_user_id
        ).first()
        
        # If not found by match ID, check if match_id was passed as the job ID instead
        if not match:
            match = uow.session.query(JobMatchORM).filter(
                JobMatchORM.job_id == match_id,
                JobMatchORM.user_id == current_user_id
            ).first()
            
        if not match:
            # 404 (Not Found) on mismatch or missing to prevent confirming existence
            raise HTTPException(status_code=404, detail="Job match not found.")

        # Load the corresponding job details
        job = uow.session.query(JobORM).filter(JobORM.id == match.job_id).first()
        if not job:
            raise HTTPException(status_code=404, detail="Job details not found.")

        # Check if rationale is missing/empty (None or "") in DB
        if not match.rationale:
            # Generate the rationale lazily
            # 1. Fetch active resume for this user to get skills
            active_resume = uow.resumes.get_active(current_user_id)
            if active_resume:
                skills_source = active_resume.get("skills") or active_resume.get("parsed_skills") or []
                resume_skills = ", ".join(skills_source)
            else:
                # Fallback to general resume index if user has no resume in DB
                from app.services.resume_index import resume_index
                resume_data = resume_index.get_resume_data() or {}
                resume_skills = ", ".join(resume_data.get("skills", []))
            
            prompt = f"""You are an AI career advisor.
Resume Skills: {resume_skills}
Job Title: {job.title} at {job.company.name if job.company else 'Unknown Company'}
Job Description: {job.description[:400]}

Write ONE sentence.
Maximum 25 words.
Mention only overlapping skills.
Do not invent experience."""
            
            try:
                rationale_text = llm_router.generate(prompt=prompt)
                # Store the generated rationale back in the match record
                match.rationale = rationale_text
                uow.commit()
            except Exception as e:
                # Log but do not fail the request completely; fall back to default
                import logging
                logging.getLogger("routes.api").error(f"Failed to generate lazy rationale: {e}", exc_info=True)

        comp_name = job.company.name if job.company else "Unknown Company"
        return {
            "id": match.id,
            "posting": {
                "id": job.id,
                "title": job.title,
                "company": comp_name,
                "description": job.description,
                "url": job.url,
                "source": job.source
            },
            "overall_score": match.score,
            "fit_rationale": match.rationale or "Pending analysis...",
            "status": match.status
        }


@router.post("/gap-report", response_model=GapReport)
async def generate_gap_report(request: GapReportRequest, current_user_id: str = Depends(get_current_user_id)):
    """
    Generates a gap report for a specific job description or URL using LangGraph.
    """
    return await gap_service.analyze_gap(request, user_id=current_user_id)


@router.get("/ingestion/status")
async def get_ingestion_status():
    """
    Returns diagnostic operational status of the latest ingestion runs and embedding queue size.
    """
    from app.repositories.uow import UnitOfWork
    from app.services.ingestion.queue import embedding_queue
    with UnitOfWork() as uow:
        latest_runs = uow.ingestion_runs.get_latest(limit=5)
    return {
        "runs": latest_runs,
        "queue_size": embedding_queue.size()
    }


@router.get("/scheduler/status")
async def get_scheduler_status():
    """
    Returns diagnostic status of the independent job scheduler and embedding worker queue.
    """
    from app.services.job_scheduler import job_scheduler
    from app.services.ingestion.queue import embedding_queue
    status_data = job_scheduler.get_status()
    status_data["queue_size"] = embedding_queue.size()
    return status_data


@router.get("/admin/dlq")
async def get_dlq():
    """
    Returns contents of the embedding Dead Letter Queue (DLQ).
    """
    from app.services.ingestion.queue import embedding_queue
    return embedding_queue.get_dlq_entries()


# In-memory fallback for SSE tickets when Redis is not running
_fallback_tickets: Dict[str, tuple[str, float]] = {}

@router.post("/stream/ticket")
async def create_stream_ticket(current_user_id: str = Depends(get_current_user_id)):
    """
    Mints a short-lived, single-purpose one-time ticket for opening the SSE stream.
    Valid for 60 seconds.
    """
    ticket_id = str(uuid.uuid4())
    
    # Store in Redis if available
    from app.services.ingestion.queue import embedding_queue
    if hasattr(embedding_queue, "queue_backend") and embedding_queue.queue_backend == "redis":
        try:
            embedding_queue.client.setex(f"sse_ticket:{ticket_id}", 60, current_user_id)
        except Exception as e:
            import logging
            logging.getLogger("routes.api").error(f"Failed to save SSE ticket to Redis: {e}")
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
            import logging
            logging.getLogger("routes.api").error(f"Failed to read/delete SSE ticket from Redis: {e}")

    # 2. Fallback to in-memory if not found in Redis
    if not user_id:
        if ticket in _fallback_tickets:
            stored_user_id, expiry = _fallback_tickets.pop(ticket)
            if time.time() <= expiry:
                user_id = stored_user_id
                
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid, expired, or already-used stream ticket."
        )
        
    async def event_gen():
        # Connect using the redis asyncio module
        client = aioredis.from_url(settings.redis_url, decode_responses=True)
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
            import logging
            logging.getLogger("routes.api").error(f"SSE stream error: {e}")
        finally:
            await pubsub.unsubscribe()
            await client.close()

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={
            "X-Accel-Buffering": "no",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive"
        }
    )


@router.get("/matches", response_model=List[ScoredPosting])
async def get_matches(
    since: Optional[str] = Query(None, description="ISO 8601 datetime string filter"),
    current_user_id: str = Depends(get_current_user_id)
):
    """
    Get job matches for the current user, optionally filtered by creation time (reconnection gap-filling).
    """
    from app.repositories.uow import UnitOfWork
    from app.models.orm import JobMatchORM, JobORM
    
    with UnitOfWork() as uow:
        query = uow.session.query(JobMatchORM, JobORM).join(
            JobORM, JobMatchORM.job_id == JobORM.id
        ).filter(
            JobMatchORM.user_id == current_user_id
        )
        
        if since is not None:
            try:
                clean_since = since.replace("Z", "+00:00") if since.endswith("Z") else since
                since_dt = datetime.fromisoformat(clean_since)
                query = query.filter(JobMatchORM.created_at >= since_dt)
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Invalid ISO 8601 format: {e}")
            
        results = query.order_by(
            JobMatchORM.score.desc(),
            JobMatchORM.created_at.desc()
        ).all()
        
        matches = []
        for match, job in results:
            comp_name = job.company.name if job.company else "Unknown Company"
            matches.append({
                "id": match.id,
                "posting": {
                    "id": job.id,
                    "title": job.title,
                    "company": comp_name,
                    "description": job.description,
                    "url": job.url,
                    "source": job.source
                },
                "overall_score": match.score,
                "fit_rationale": match.rationale or "Pending analysis...",
                "status": match.status
            })
        return matches


@router.get("/profile", response_model=UserProfileSchema)
async def get_profile(current_user_id: str = Depends(get_current_user_id)):
    """Retrieve profile settings of the current user."""
    from app.repositories.uow import UnitOfWork
    with UnitOfWork() as uow:
        user = uow.users.get_by_id(current_user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User profile not found.")
        return user


@router.put("/profile", response_model=UserProfileSchema)
async def update_profile(
    profile_data: UserProfileUpdateSchema,
    current_user_id: str = Depends(get_current_user_id)
):
    """
    Update profile settings of the current user.
    Enforces validation rule: notify_threshold >= display_threshold.
    """
    from app.repositories.uow import UnitOfWork
    from app.models.orm import UserORM
    with UnitOfWork() as uow:
        user = uow.session.query(UserORM).filter(UserORM.id == current_user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User profile not found.")

        target_display = profile_data.display_threshold if profile_data.display_threshold is not None else user.display_threshold
        target_notify = profile_data.notify_threshold if profile_data.notify_threshold is not None else user.notify_threshold

        if target_notify < target_display:
            raise HTTPException(
                status_code=400,
                detail=f"Validation failed: Notification threshold ({target_notify}) cannot be lower than display threshold ({target_display}).",
            )

        updated_user = uow.users.update(
            user_id=current_user_id,
            name=profile_data.name,
            email=profile_data.email,
            whatsapp_number=profile_data.whatsapp_number,
            notify_threshold=profile_data.notify_threshold,
            display_threshold=profile_data.display_threshold
        )
        uow.commit()
        return updated_user


class TokenRotateConfirm(BaseModel):
    confirm: bool


@router.post("/profile/rotate-token")
async def rotate_token(
    body: TokenRotateConfirm,
    current_user_id: str = Depends(get_current_user_id),
):
    """
    Rotate the API token for the current user.

    This is a one-way, immediately irreversible action:
    - The old token is invalidated the moment this request commits.
    - The new raw token is returned **once** and cannot be retrieved again.
    - There is no grace period \u2014 any in-flight requests using the old token
      will fail after this call completes.

    Requires {"confirm": true} in the request body to prevent accidental
    self-lockout from retried requests or stray UI clicks.
    """
    if not body.confirm:
        raise HTTPException(
            status_code=400,
            detail='Set "confirm": true in the request body to proceed with token rotation.',
        )

    import secrets
    import hashlib

    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()

    from app.repositories.uow import UnitOfWork

    with UnitOfWork() as uow:
        success = uow.users.update_token_hash(current_user_id, token_hash)
        if not success:
            raise HTTPException(status_code=404, detail="User not found.")
        uow.commit()

    import logging
    logging.getLogger("routes.api").info(
        f"Token rotated for user {current_user_id}. Old token invalidated."
    )

    return {
        "message": (
            "Token rotated successfully. "
            "Store the new token securely \u2014 it will not be shown again."
        ),
        "new_token": raw_token,
    }


class SignupRequest(BaseModel):
    name: str
    email: str
    invite_code: str
    whatsapp_number: Optional[str] = None
    title: Optional[str] = "AI Engineer"
    years_experience: Optional[float] = 0.0
    skills: Optional[List[str]] = []
    projects: Optional[List[Dict[str, Any]]] = []


@router.post("/auth/signup")
async def signup(request: SignupRequest):
    """
    Self-serve user onboarding endpoint.
    Requires a valid invite code matching SIGNUP_INVITE_TOKEN.
    Creates user, generates raw API token (returned ONCE), and seeds initial resume embedding.
    """
    import secrets
    import hashlib
    from app.repositories.uow import UnitOfWork

    # 1. Invite token verification using constant-time comparison
    if not request.invite_code or not secrets.compare_digest(request.invite_code, settings.signup_invite_token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing signup invite code."
        )

    # 2. Email uniqueness check & user creation
    with UnitOfWork() as uow:
        existing = uow.users.get_by_email(request.email)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A user with this email address is already registered."
            )

        user_id = str(uuid.uuid4())
        raw_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()

        user = uow.users.create(
            name=request.name,
            email=request.email,
            user_id=user_id,
            whatsapp_number=request.whatsapp_number,
            token_hash=token_hash
        )

        # 3. Create initial active resume and compute vector embeddings
        uow.resumes.upsert_resume(
            user_id=user_id,
            title=request.title or "AI Engineer",
            years_experience=request.years_experience or 0.0,
            skills=request.skills or [],
            projects=request.projects or []
        )
        uow.commit()

    return {
        "user": user,
        "raw_token": raw_token,
        "message": "Account created successfully. Pass 'Authorization: Bearer <raw_token>' in HTTP headers."
    }

