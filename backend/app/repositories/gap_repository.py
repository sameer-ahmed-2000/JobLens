from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from app.models.orm import GapReportORM
from app.models.schemas import GapReport

class GapRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_cached_report(self, job_id: str, user_id: str, resume_version: int = 1) -> Optional[GapReport]:
        report_orm = self.session.query(GapReportORM).filter(
            GapReportORM.job_id == job_id,
            GapReportORM.user_id == user_id,
            GapReportORM.resume_version == resume_version
        ).order_by(GapReportORM.generated_at.desc()).first()
        if not report_orm or not report_orm.report_data:
            return None
        try:
            return GapReport(**report_orm.report_data)
        except Exception:
            return None

    def save_report(
        self,
        job_id: str,
        user_id: str,
        resume_version: int,
        report: GapReport
    ) -> GapReport:
        report_data = report.dict() if hasattr(report, "dict") else report.model_dump()
        report_orm = GapReportORM(
            job_id=job_id,
            user_id=user_id,
            resume_version=resume_version,
            confidence_score=report.confidence_score,
            overall_summary=report.overall_recommendation or report.overall_fit_summary or "Gap Report generated.",
            report_data=report_data
        )
        self.session.add(report_orm)
        self.session.flush()
        return report
