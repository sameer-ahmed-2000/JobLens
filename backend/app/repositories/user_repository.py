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
        return self._to_dict(user)

    def get_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        user = self.session.query(UserORM).filter(UserORM.email == email).first()
        if not user:
            return None
        return self._to_dict(user)

    def get_by_token_hash(self, token_hash: str) -> Optional[Dict[str, Any]]:
        user = self.session.query(UserORM).filter(UserORM.token_hash == token_hash).first()
        if not user:
            return None
        return self._to_dict(user)

    def create(
        self,
        name: str,
        email: str,
        user_id: Optional[str] = None,
        whatsapp_number: Optional[str] = None,
        notify_threshold: float = 0.85,
        display_threshold: float = 0.70,
        token_hash: Optional[str] = None
    ) -> Dict[str, Any]:
        user = UserORM(
            name=name,
            email=email,
            whatsapp_number=whatsapp_number,
            notify_threshold=notify_threshold,
            display_threshold=display_threshold,
            token_hash=token_hash
        )
        if user_id:
            user.id = user_id
        self.session.add(user)
        self.session.flush()
        return self._to_dict(user)

    def update_token_hash(self, user_id: str, token_hash: str) -> bool:
        """Atomically replace a user's stored token hash, invalidating the old token immediately."""
        user = self.session.query(UserORM).filter(UserORM.id == user_id).first()
        if not user:
            return False
        user.token_hash = token_hash
        self.session.flush()
        return True

    def update(
        self,
        user_id: str,
        name: Optional[str] = None,
        email: Optional[str] = None,
        whatsapp_number: Optional[str] = None,
        notify_threshold: Optional[float] = None,
        display_threshold: Optional[float] = None
    ) -> Optional[Dict[str, Any]]:
        user = self.session.query(UserORM).filter(UserORM.id == user_id).first()
        if not user:
            return None
        if name is not None:
            user.name = name
        if email is not None:
            user.email = email
        user.whatsapp_number = whatsapp_number
        if notify_threshold is not None:
            user.notify_threshold = notify_threshold
        if display_threshold is not None:
            user.display_threshold = display_threshold
        self.session.flush()
        return self._to_dict(user)

    def _to_dict(self, user: UserORM) -> Dict[str, Any]:
        return {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "whatsapp_number": user.whatsapp_number,
            "notify_threshold": user.notify_threshold,
            "display_threshold": user.display_threshold,
            "token_hash": user.token_hash,
            "created_at": user.created_at
        }
