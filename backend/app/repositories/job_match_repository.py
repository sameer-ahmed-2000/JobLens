from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict, Any
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session
from app.models.orm import JobMatchORM, JobORM, ApplicationORM
from app.config import settings

class JobMatchRepository:
    def __init__(self, session: Session):
        self.session = session

    def upsert(
        self,
        user_id: str,
        job_id: str,
        score: float,
        rationale: Optional[str] = None,
        status: str = "new"
    ) -> Dict[str, Any]:
        """Alias for upsert_match to match scoring service expectations."""
        return self.upsert_match(user_id, job_id, score, rationale, status)

    def upsert_match(
        self,
        user_id: str,
        job_id: str,
        score: float,
        rationale: Optional[str] = None,
        status: str = "new",
        match_id: Optional[str] = None,
        score_breakdown: Optional[Dict[str, Any]] = None,
        scoring_version: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Upsert a job match scoring record.
        CRITICAL: If the row already exists, update only score and rationale,
        preserving the current user-assigned status (e.g. Applied, Dismissed).
        """
        match = self.session.query(JobMatchORM).filter(
            JobMatchORM.user_id == user_id,
            JobMatchORM.job_id == job_id
        ).first()

        if match:
            match.score = score
            if rationale:
                match.rationale = rationale
            if status != "new":
                match.status = status
            if score_breakdown is not None:
                match.score_breakdown = score_breakdown
            if scoring_version is not None:
                match.scoring_version = scoring_version
        else:
            match = JobMatchORM(
                user_id=user_id,
                job_id=job_id,
                score=score,
                rationale=rationale,
                status=status,
                score_breakdown=score_breakdown,
                scoring_version=scoring_version or "v1",
            )

            if match_id:
                match.id = match_id
            self.session.add(match)

        self.session.flush()
        return self._to_dict(match)

    def upsert_matches(self, user_id: str, scored_postings: List[Any]) -> None:
        """Batch upsert multiple scored postings for a user."""
        for sp in scored_postings:
            posting = sp.posting if hasattr(sp, "posting") else sp.get("posting")
            overall_score = sp.overall_score if hasattr(sp, "overall_score") else sp.get("overall_score")
            fit_rationale = sp.fit_rationale if hasattr(sp, "fit_rationale") else sp.get("fit_rationale")
            
            job_id = posting.id if hasattr(posting, "id") else posting.get("id")
            
            self.upsert_match(
                user_id=user_id,
                job_id=job_id,
                score=overall_score,
                rationale=fit_rationale
            )

    def get_matches_for_user(self, user_id: str, min_score: Optional[float] = None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Retrieve job matches for a user, ordered by score descending, then created_at descending.
        Joins with the JobORM/CompanyORM tables to enrich output.

        Filters to matches at/above `min_score` (defaults to the user's own
        display_threshold if not passed) and caps result count at `limit` if specified.
        """
        from app.models.orm import UserORM

        if min_score is None:
            user = self.session.query(UserORM).filter(UserORM.id == user_id).first()
            min_score = user.display_threshold if user else 0.7

        stale_threshold = datetime.now(timezone.utc) - timedelta(days=settings.job_stale_after_days)


        query = self.session.query(JobMatchORM, JobORM).join(
            JobORM, JobMatchORM.job_id == JobORM.id
        ).outerjoin(
            ApplicationORM,
            and_(
                ApplicationORM.job_id == JobORM.id,
                ApplicationORM.user_id == user_id
            )
        ).filter(
            JobMatchORM.user_id == user_id,
            JobMatchORM.score >= min_score,
            or_(
                JobORM.last_seen_at >= stale_threshold,
                ApplicationORM.id.isnot(None)
            )
        ).group_by(
            JobMatchORM.id, JobORM.id
        ).order_by(
            JobMatchORM.score.desc(),
            JobMatchORM.created_at.desc()
        )

        if limit is not None:
            query = query.limit(limit)

        results = query.all()

        matches = []
        for match, job in results:
            comp_name = "Unknown Company"
            if job.company:
                comp_name = job.company.name

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
                "status": match.status,
                "score_breakdown": match.score_breakdown,
                "scoring_version": match.scoring_version,
            })
        return matches

    def _to_dict(self, match: JobMatchORM) -> Dict[str, Any]:
        return {
            "id": match.id,
            "user_id": match.user_id,
            "job_id": match.job_id,
            "score": match.score,
            "rationale": match.rationale,
            "status": match.status,
            "score_breakdown": match.score_breakdown,
            "scoring_version": match.scoring_version,
            "created_at": match.created_at
        }
