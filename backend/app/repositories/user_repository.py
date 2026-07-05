from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from app.models.orm import UserORM

class UserRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        user = self.session.query(UserORM).filter(UserORM.id == user_id).first()
        if not user:
            return None
        return {"id": user.id, "name": user.name, "email": user.email, "created_at": user.created_at}

    def get_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        user = self.session.query(UserORM).filter(UserORM.email == email).first()
        if not user:
            return None
        return {"id": user.id, "name": user.name, "email": user.email, "created_at": user.created_at}

    def create(self, name: str, email: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        user = UserORM(name=name, email=email)
        if user_id:
            user.id = user_id
        self.session.add(user)
        self.session.flush()
        return {"id": user.id, "name": user.name, "email": user.email, "created_at": user.created_at}
