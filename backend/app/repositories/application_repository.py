from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.models.orm import ApplicationORM, JobORM, CompanyORM, GapReportORM

VALID_STATUSES = [
    "Saved",
    "Applied",
    "Assessment",
    "Online Assessment",
    "Technical Interview",
    "Manager Interview",
    "HR Interview",
    "Offer",
    "Rejected",
    "Withdrawn",
]


class ApplicationRepository:
    def __init__(self, session: Session):
        self.session = session

    # ──────────────────────────────────────────────────
    # Query
    # ──────────────────────────────────────────────────

    def get_application(self, app_id: str) -> Optional[Dict[str, Any]]:
        app = self.session.query(ApplicationORM).filter(ApplicationORM.id == app_id).first()
        return self._to_dict(app) if app else None

    # Keep old name as alias for backwards compatibility
    def get_by_id(self, app_id: str) -> Optional[Dict[str, Any]]:
        return self.get_application(app_id)

    def get_by_user(self, user_id: str) -> List[Dict[str, Any]]:
        apps = (
            self.session.query(ApplicationORM)
            .filter(ApplicationORM.user_id == user_id)
            .order_by(ApplicationORM.updated_at.desc())
            .all()
        )
        return [self._to_dict(a) for a in apps]

    # Alias used by new routes
    def list_applications(self, user_id: str) -> List[Dict[str, Any]]:
        return self.get_by_user(user_id)

    def application_exists(self, user_id: str, job_id: str) -> bool:
        return (
            self.session.query(ApplicationORM)
            .filter(ApplicationORM.user_id == user_id, ApplicationORM.job_id == job_id)
            .first()
        ) is not None

    def get_by_job(self, user_id: str, job_id: str) -> Optional[Dict[str, Any]]:
        app = (
            self.session.query(ApplicationORM)
            .filter(ApplicationORM.user_id == user_id, ApplicationORM.job_id == job_id)
            .first()
        )
        return self._to_dict(app) if app else None

    # ──────────────────────────────────────────────────
    # Mutations
    # ──────────────────────────────────────────────────

    def save_application(
        self,
        user_id: str,
        job_id: str,
        resume_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a new application with status='Saved'. Raises ValueError on duplicate."""
        if self.application_exists(user_id, job_id):
            raise ValueError(f"Application already exists for job_id={job_id}")
        now = datetime.utcnow()
        app = ApplicationORM(
            user_id=user_id,
            job_id=job_id,
            resume_id=resume_id,
            status="Saved",
            created_at=now,
            updated_at=now,
        )
        self.session.add(app)
        self.session.flush()
        return self._to_dict(app)

    # Keep old name as alias
    def create(self, user_id: str, job_id: str, status: str = "Saved", notes: Optional[str] = None) -> Dict[str, Any]:
        if self.application_exists(user_id, job_id):
            raise ValueError(f"Application already exists for job_id={job_id}")
        now = datetime.utcnow()
        app = ApplicationORM(user_id=user_id, job_id=job_id, status=status, notes=notes, created_at=now, updated_at=now)
        self.session.add(app)
        self.session.flush()
        return self._to_dict(app)

    def update_status(
        self,
        app_id: str,
        status: str,
        notes: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        if status not in VALID_STATUSES:
            raise ValueError(f"Invalid status: {status}. Must be one of {VALID_STATUSES}")
        app = self.session.query(ApplicationORM).filter(ApplicationORM.id == app_id).first()
        if not app:
            return None
        app.status = status
        app.updated_at = datetime.utcnow()
        if notes is not None:
            app.notes = notes
        self.session.flush()
        return self._to_dict(app)

    def delete_application(self, app_id: str) -> bool:
        app = self.session.query(ApplicationORM).filter(ApplicationORM.id == app_id).first()
        if not app:
            return False
        self.session.delete(app)
        self.session.flush()
        return True

    # ──────────────────────────────────────────────────
    # Serialization
    # ──────────────────────────────────────────────────

    def _to_dict(self, app: ApplicationORM) -> Dict[str, Any]:
        # Enrich with job + company data
        job_title = "Unknown Role"
        company = "Unknown Company"
        job_url: Optional[str] = None
        match_score: Optional[float] = None
        confidence_score: Optional[float] = None

        if app.job_id:
            job: Optional[JobORM] = self.session.get(JobORM, app.job_id)
            if job:
                job_title = job.title
                job_url = job.url
                if job.company:
                    company = job.company.name
                elif job.company_id:
                    comp: Optional[CompanyORM] = self.session.get(CompanyORM, job.company_id)
                    if comp:
                        company = comp.name

        # Fetch latest gap report scores for this job/user pair
        if app.job_id and app.user_id:
            latest_gap: Optional[GapReportORM] = (
                self.session.query(GapReportORM)
                .filter(
                    GapReportORM.job_id == app.job_id,
                    GapReportORM.user_id == app.user_id,
                )
                .order_by(GapReportORM.generated_at.desc())
                .first()
            )
            if latest_gap and latest_gap.report_data:
                match_score = latest_gap.report_data.get("match_score")
                confidence_score = latest_gap.confidence_score

        return {
            "id": app.id,
            "user_id": app.user_id,
            "job_id": app.job_id,
            "resume_id": app.resume_id,
            "job_title": job_title,
            "company": company,
            "job_url": job_url,
            "status": app.status,
            "notes": app.notes,
            "match_score": match_score,
            "confidence_score": confidence_score,
            "created_at": app.created_at,
            "updated_at": app.updated_at,
        }
