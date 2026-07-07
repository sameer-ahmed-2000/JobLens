from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from app.models.orm import IngestionRunORM

class IngestionRunRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(self, source: str, status: str = "Running") -> Dict[str, Any]:
        run = IngestionRunORM(
            source=source,
            status=status,
            started_at=datetime.utcnow()
        )
        self.session.add(run)
        self.session.flush()
        return self._to_dict(run)

    def update(
        self,
        run_id: str,
        completed_at: Optional[datetime] = None,
        jobs_fetched: Optional[int] = None,
        jobs_inserted: Optional[int] = None,
        jobs_updated: Optional[int] = None,
        duplicates_removed: Optional[int] = None,
        failures: Optional[int] = None,
        duration_ms: Optional[float] = None,
        status: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        run = self.session.query(IngestionRunORM).filter(IngestionRunORM.id == run_id).first()
        if not run:
            return None
        if completed_at is not None:
            run.completed_at = completed_at
        if jobs_fetched is not None:
            run.jobs_fetched = jobs_fetched
        if jobs_inserted is not None:
            run.jobs_inserted = jobs_inserted
        if jobs_updated is not None:
            run.jobs_updated = jobs_updated
        if duplicates_removed is not None:
            run.duplicates_removed = duplicates_removed
        if failures is not None:
            run.failures = failures
        if duration_ms is not None:
            run.duration_ms = duration_ms
        if status is not None:
            run.status = status
        self.session.flush()
        return self._to_dict(run)

    def get_latest(self, limit: int = 10) -> List[Dict[str, Any]]:
        runs = self.session.query(IngestionRunORM).order_by(IngestionRunORM.started_at.desc()).limit(limit).all()
        return [self._to_dict(r) for r in runs]

    def _to_dict(self, run: IngestionRunORM) -> Dict[str, Any]:
        return {
            "id": run.id,
            "started_at": run.started_at.isoformat() if run.started_at else None,
            "completed_at": run.completed_at.isoformat() if run.completed_at else None,
            "source": run.source,
            "jobs_fetched": run.jobs_fetched,
            "jobs_inserted": run.jobs_inserted,
            "jobs_updated": run.jobs_updated,
            "duplicates_removed": run.duplicates_removed,
            "failures": run.failures,
            "duration_ms": run.duration_ms,
            "status": run.status
        }
