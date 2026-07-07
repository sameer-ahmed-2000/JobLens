import logging
from typing import Dict, Any, Optional
from sqlalchemy import func
from app.repositories.uow import UnitOfWork
from app.models.orm import ApplicationORM, GapReportORM

logger = logging.getLogger("dashboard_service")

# Status groupings for metric aggregation
ASSESSMENT_STATUSES = {"Assessment", "Online Assessment"}
INTERVIEW_STATUSES = {"Technical Interview", "Manager Interview", "HR Interview"}
OFFER_STATUS = "Offer"
REJECTED_STATUS = "Rejected"
APPLIED_STATUS = "Applied"
SAVED_STATUS = "Saved"


class DashboardService:
    def get_metrics(self, user_id: str) -> Dict[str, Any]:
        """
        Aggregate Career Workspace metrics for a user.

        Returns counts by status category, success rate, and average AI scores.
        """
        try:
            with UnitOfWork() as uow:
                session = uow.session

                # Count applications per status for this user
                status_counts = (
                    session.query(ApplicationORM.status, func.count(ApplicationORM.id).label("cnt"))
                    .filter(ApplicationORM.user_id == user_id)
                    .group_by(ApplicationORM.status)
                    .all()
                )

                counts: Dict[str, int] = {row.status: row.cnt for row in status_counts}

                saved = counts.get(SAVED_STATUS, 0)
                applied = counts.get(APPLIED_STATUS, 0)
                assessments = sum(counts.get(s, 0) for s in ASSESSMENT_STATUSES)
                interviews = sum(counts.get(s, 0) for s in INTERVIEW_STATUSES)
                offers = counts.get(OFFER_STATUS, 0)
                rejected = counts.get(REJECTED_STATUS, 0)
                withdrawn = counts.get("Withdrawn", 0)
                total = sum(counts.values())

                # Success rate: offers / (applied + assessments + interviews + offers + rejected) * 100
                funnel_total = applied + assessments + interviews + offers + rejected
                success_rate = round((offers / funnel_total) * 100, 1) if funnel_total > 0 else 0.0

                # Average match score and confidence from gap reports linked to user's applications
                gap_stats = (
                    session.query(
                        func.avg(GapReportORM.confidence_score).label("avg_confidence"),
                    )
                    .filter(GapReportORM.user_id == user_id)
                    .first()
                )
                avg_confidence = round(float(gap_stats.avg_confidence), 1) if gap_stats and gap_stats.avg_confidence else 0.0

                # Average match score from report_data JSON field
                # Fetch all reports and average in Python (JSON extraction is DB-specific)
                all_reports = (
                    session.query(GapReportORM)
                    .filter(GapReportORM.user_id == user_id, GapReportORM.report_data.isnot(None))
                    .all()
                )
                match_scores = [
                    r.report_data.get("match_score")
                    for r in all_reports
                    if r.report_data and r.report_data.get("match_score") is not None
                ]
                avg_match_score = round(sum(match_scores) / len(match_scores), 1) if match_scores else 0.0

                # Average days in pipeline (from created_at to updated_at)
                from datetime import datetime
                pipeline_apps = (
                    session.query(ApplicationORM)
                    .filter(
                        ApplicationORM.user_id == user_id,
                        ApplicationORM.created_at.isnot(None),
                        ApplicationORM.status.notin_(["Saved"]),
                    )
                    .all()
                )
                days_list = []
                for app in pipeline_apps:
                    if app.created_at and app.updated_at:
                        delta = (app.updated_at - app.created_at).days
                        days_list.append(delta)
                avg_days_in_pipeline = round(sum(days_list) / len(days_list), 1) if days_list else 0.0

                return {
                    "saved": saved,
                    "applied": applied,
                    "assessments": assessments,
                    "interviews": interviews,
                    "offers": offers,
                    "rejected": rejected,
                    "withdrawn": withdrawn,
                    "total": total,
                    "success_rate": success_rate,
                    "average_match_score": avg_match_score,
                    "average_confidence": avg_confidence,
                    "avg_days_in_pipeline": avg_days_in_pipeline,
                }

        except Exception as e:
            logger.error(f"Dashboard metrics error: {e}", exc_info=True)
            # Return safe zero-state so the UI never crashes
            return {
                "saved": 0,
                "applied": 0,
                "assessments": 0,
                "interviews": 0,
                "offers": 0,
                "rejected": 0,
                "withdrawn": 0,
                "total": 0,
                "success_rate": 0.0,
                "average_match_score": 0.0,
                "average_confidence": 0.0,
                "avg_days_in_pipeline": 0.0,
            }


dashboard_service = DashboardService()
