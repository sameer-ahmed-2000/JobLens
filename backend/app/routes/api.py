import json
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request, BackgroundTasks

from app.models.schemas import (
    ScoredPosting, GapReportRequest, GapReport, UserProfileSchema,
    UserProfileUpdateSchema, NotificationItemSchema
)
from app.routes.auth import get_current_user_id
from app.rate_limiter import limiter
from app.services.discovery_service import discovery_service
from app.services.gap_service import gap_service
from pydantic import BaseModel

# Backward compatibility re-exports for tests/modules importing from app.routes.api
from app.routes.matches import get_matches, get_match_detail
from app.routes.resumes import (
    upload_resume, get_latest_resume_status, get_resume_status,
    reprocess_resume, download_resume, get_active_resume
)
from app.routes.streaming import create_stream_ticket, stream_jobs
from app.routes.admin import get_ingestion_status, get_scheduler_status, get_dlq

logger = logging.getLogger(__name__)

router = APIRouter()



@router.get("/postings", response_model=List[ScoredPosting])
async def get_postings(
    min_score: Optional[float] = None,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
    current_user_id: str = Depends(get_current_user_id)
):
    """
    Returns a list of job postings, scored and ranked against the user's resume.
    """
    return await discovery_service.get_ranked_postings(
        user_id=current_user_id, force_refresh=False, min_score=min_score, limit=limit, offset=offset
    )


@router.post("/refetch")
@limiter.limit("3/minute")
async def refetch_jobs(
    request: Request,
    background_tasks: BackgroundTasks,
    current_user_id: str = Depends(get_current_user_id)
):
    """
    User-triggered "find new jobs now" action. Runs ingestion + scoring in background.
    """
    import redis
    from app.services.resume_index import resume_index
    from app.services.job_scheduler import job_scheduler
    from app.config import settings

    def _run_refetch(user_id: str):
        keywords = resume_index.get_search_keywords(user_id=user_id)
        if not keywords:
            logger.warning(f"Refetch skipped for {user_id}: no resume keywords available.")
            _publish_refetch_status(user_id, "skipped_no_resume")
            return
        try:
            stats = job_scheduler.trigger_live_search(keywords=keywords, force=True)
            _publish_refetch_status(user_id, "completed", stats)
        except Exception as e:
            logger.error(f"Background refetch failed for {user_id}: {e}", exc_info=True)
            _publish_refetch_status(user_id, "failed")

    def _publish_refetch_status(user_id: str, status_val: str, stats: dict = None):
        try:
            from app.redis_client import get_redis_client
            client = get_redis_client()
            payload = {"type": "refetch_status", "status": status_val, "stats": stats or {}}
            client.publish(f"job_events:{user_id}", json.dumps(payload))
        except Exception as e:
            logger.warning(f"Could not publish refetch status for {user_id}: {e}")


    background_tasks.add_task(_run_refetch, current_user_id)
    return {"status": "started", "message": "Refetching jobs in the background -- new matches will appear live."}


@router.post("/discover", response_model=List[ScoredPosting])
@limiter.limit("10/minute")
async def trigger_discovery(
    request: Request,
    background_tasks: BackgroundTasks,
    force_live_search: bool = False,
    current_user_id: str = Depends(get_current_user_id)
):
    """
    Triggers discovery pipeline and scores/ranks combined job pool via LangGraph.
    """
    from app.services.resume_index import resume_index
    from app.services.job_scheduler import job_scheduler
    from app.services.scoring_service import scoring_service

    try:
        scoring_service.cache.refresh()
    except Exception as e:
        logger.error(f"Failed to refresh active resume cache: {e}")

    keywords = resume_index.get_search_keywords(user_id=current_user_id)
    if keywords:
        background_tasks.add_task(
            job_scheduler.trigger_live_search,
            keywords=keywords,
            force=force_live_search
        )

    return await discovery_service.get_ranked_postings(user_id=current_user_id, force_refresh=False)


@router.post("/gap-report", response_model=GapReport)
async def generate_gap_report(request: GapReportRequest, current_user_id: str = Depends(get_current_user_id)):
    """
    Generates a gap report for a specific job description or URL using LangGraph.
    """
    return await gap_service.analyze_gap(request, user_id=current_user_id)


@router.get("/profile", response_model=UserProfileSchema)
def get_profile(current_user_id: str = Depends(get_current_user_id)):
    """Retrieve profile settings of the current user."""
    from app.repositories.uow import UnitOfWork
    with UnitOfWork() as uow:
        user = uow.users.get_by_id(current_user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User profile not found.")
        return user


@router.put("/profile", response_model=UserProfileSchema)
def update_profile(
    profile_data: UserProfileUpdateSchema,
    current_user_id: str = Depends(get_current_user_id)
):
    """
    Update profile settings of the current user.
    """
    from app.repositories.uow import UnitOfWork
    from app.models.orm import UserORM
    with UnitOfWork() as uow:
        user = uow.session.query(UserORM).filter(UserORM.id == current_user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User profile not found.")

        MIN_DISPLAY_THRESHOLD = 0.4

        target_display = profile_data.display_threshold if profile_data.display_threshold is not None else user.display_threshold
        if target_display < MIN_DISPLAY_THRESHOLD:
            raise HTTPException(
                status_code=400,
                detail=f"Display threshold cannot be set below {MIN_DISPLAY_THRESHOLD:.0%} -- matches below this floor are considered too weak to be useful."
            )

        target_notify = profile_data.notify_threshold if profile_data.notify_threshold is not None else user.notify_threshold

        if target_notify < target_display:
            raise HTTPException(
                status_code=400,
                detail=f"Validation failed: Notification threshold ({target_notify}) cannot be lower than display threshold ({target_display}).",
            )

        if profile_data.timezone:
            import zoneinfo
            try:
                zoneinfo.ZoneInfo(profile_data.timezone.strip())
            except Exception:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid IANA timezone string: '{profile_data.timezone}'."
                )

        updated_user = uow.users.update(
            user_id=current_user_id,
            name=profile_data.name,
            email=profile_data.email,
            whatsapp_number=profile_data.whatsapp_number,
            notify_threshold=profile_data.notify_threshold,
            display_threshold=profile_data.display_threshold,
            quiet_hours_start=profile_data.quiet_hours_start,
            quiet_hours_end=profile_data.quiet_hours_end,
            timezone=profile_data.timezone,
            manual_core_skills=profile_data.manual_core_skills,
            manual_target_role=profile_data.manual_target_role
        )
        uow.commit()
        return updated_user


@router.get("/notifications", response_model=List[NotificationItemSchema])
def get_notification_history(current_user_id: str = Depends(get_current_user_id)):
    """
    Retrieves in-app notification history for the current user.
    """
    from app.repositories.uow import UnitOfWork
    from app.models.orm import JobMatchORM, JobORM, UserORM

    with UnitOfWork() as uow:
        user = uow.session.query(UserORM).filter(UserORM.id == current_user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User profile not found.")

        results = uow.session.query(JobMatchORM, JobORM).join(
            JobORM, JobMatchORM.job_id == JobORM.id
        ).filter(
            JobMatchORM.user_id == current_user_id,
            JobMatchORM.score >= user.notify_threshold
        ).order_by(JobMatchORM.created_at.desc()).all()

        notifications = []
        for match, job in results:
            comp_name = job.company.name if job.company else "Unknown Company"
            notifications.append({
                "id": match.id,
                "job_id": job.id,
                "title": job.title,
                "company": comp_name,
                "score": match.score,
                "rationale": match.rationale or "Fits your background skills.",
                "url": job.url,
                "created_at": match.created_at,
                "notified_at": match.notified_at
            })
        return notifications


class TokenRotateConfirm(BaseModel):
    confirm: bool


@router.post("/profile/rotate-token")
def rotate_token(
    body: TokenRotateConfirm,
    current_user_id: str = Depends(get_current_user_id),
):
    """
    Rotate the API token for the current user.
    """
    if not body.confirm:
        raise HTTPException(
            status_code=400,
            detail='Set "confirm": true in the request body to proceed with token rotation.',
        )

    import secrets
    import hashlib
    from app.repositories.uow import UnitOfWork

    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()

    with UnitOfWork() as uow:
        success = uow.users.update_token_hash(current_user_id, token_hash)
        if not success:
            raise HTTPException(status_code=404, detail="User not found.")
        uow.commit()

    logger.info(f"Token rotated for user {current_user_id}. Old token invalidated.")

    return {
        "message": "Token rotated successfully. Store the new token securely -- it will not be shown again.",
        "new_token": raw_token,
    }


