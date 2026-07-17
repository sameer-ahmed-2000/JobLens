from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from app.models.orm import JobMatchORM, JobORM

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
        status: str = "new"
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
            if rationale is not None:
                match.rationale = rationale
        else:
            match = JobMatchORM(
                user_id=user_id,
                job_id=job_id,
                score=score,
                rationale=rationale,
                status=status
            )
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

    def get_matches_for_user(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Retrieve all job matches for a user, ordered by score descending, then created_at descending.
        Joins with the JobORM/CompanyORM tables to enrich output.
        """
        results = self.session.query(JobMatchORM, JobORM).join(
            JobORM, JobMatchORM.job_id == JobORM.id
        ).filter(
            JobMatchORM.user_id == user_id
        ).order_by(
            JobMatchORM.score.desc(),
            JobMatchORM.created_at.desc()
        ).all()

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
                    "source": job.source
                },
                "overall_score": match.score,
                "fit_rationale": match.rationale or "Pending analysis...",
                "status": match.status
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
            "created_at": match.created_at
        }
