from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from app.models.orm import ApplicationORM

class ApplicationRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_by_id(self, app_id: str) -> Optional[Dict[str, Any]]:
        app = self.session.query(ApplicationORM).filter(ApplicationORM.id == app_id).first()
        return self._to_dict(app) if app else None

    def get_by_user(self, user_id: str) -> List[Dict[str, Any]]:
        apps = self.session.query(ApplicationORM).filter(ApplicationORM.user_id == user_id).all()
        return [self._to_dict(a) for a in apps]

    def create(self, user_id: str, job_id: str, status: str = "Saved", notes: Optional[str] = None) -> Dict[str, Any]:
        app = ApplicationORM(user_id=user_id, job_id=job_id, status=status, notes=notes)
        self.session.add(app)
        self.session.flush()
        return self._to_dict(app)

    def update_status(self, app_id: str, status: str, notes: Optional[str] = None) -> Optional[Dict[str, Any]]:
        app = self.session.query(ApplicationORM).filter(ApplicationORM.id == app_id).first()
        if not app:
            return None
        app.status = status
        if notes is not None:
            app.notes = notes
        self.session.flush()
        return self._to_dict(app)

    def _to_dict(self, app: ApplicationORM) -> Dict[str, Any]:
        return {
            "id": app.id,
            "user_id": app.user_id,
            "job_id": app.job_id,
            "status": app.status,
            "notes": app.notes,
            "updated_at": app.updated_at
        }
