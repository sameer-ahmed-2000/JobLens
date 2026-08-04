import logging
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, Query, HTTPException, Request

from app.models.schemas import ScoredPosting
from app.routes.auth import get_current_user_id
from app.rate_limiter import limiter

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/matches", response_model=List[ScoredPosting])
def get_matches(
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
                clean_since = since.strip().replace(" ", "+")
                if clean_since.endswith("Z"):
                    clean_since = clean_since.replace("Z", "+00:00")
                since_dt = datetime.fromisoformat(clean_since)
                if since_dt.tzinfo is not None:
                    from datetime import timezone
                    since_dt = since_dt.astimezone(timezone.utc).replace(tzinfo=None)
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
                    "source": job.source,
                    "last_seen_at": job.last_seen_at.isoformat() if job.last_seen_at else None
                },
                "overall_score": match.score,
                "fit_rationale": match.rationale or "Pending analysis...",
                "status": match.status
            })
        return matches


@router.get("/matches/{match_id}", response_model=ScoredPosting)
@limiter.limit("10/minute")
def get_match_detail(request: Request, match_id: str, current_user_id: str = Depends(get_current_user_id)):

    """
    Get job match detail. If fit_rationale is missing/empty in the database,
    triggers lazy rationale generation via LLM and caches the result.
    Enforces ownership check (must belong to current_user_id) and returns 404 on mismatch.
    """
    from app.repositories.uow import UnitOfWork
    from app.models.orm import JobMatchORM, JobORM
    from app.services.llm_router_factory import get_llm_router

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
            active_resume = uow.resumes.get_active(current_user_id)
            if active_resume:
                skills_source = active_resume.get("skills") or active_resume.get("parsed_skills") or []
                resume_skills = ", ".join(skills_source)
            else:
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
                rationale_text = get_llm_router("rationale").generate(prompt=prompt)
                match.rationale = rationale_text
                uow.commit()
            except Exception as e:
                logger.error(f"Failed to generate lazy rationale: {e}", exc_info=True)

        comp_name = job.company.name if job.company else "Unknown Company"
        return {
            "id": match.id,
            "posting": {
                "id": job.id,
                "title": job.title,
                "company": comp_name,
                "description": job.description,
                "url": job.url,
                "source": job.source,
                "last_seen_at": job.last_seen_at.isoformat() if job.last_seen_at else None
            },
            "overall_score": match.score,
            "fit_rationale": match.rationale or "Pending analysis...",
            "status": match.status
        }
