from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
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
        token_hash: Optional[str] = None,
        hashed_password: Optional[str] = None,
        quiet_hours_start: Optional[str] = None,
        quiet_hours_end: Optional[str] = None,
        timezone: Optional[str] = "Asia/Kolkata"
    ) -> Dict[str, Any]:
        user = UserORM(
            name=name,
            email=email,
            whatsapp_number=whatsapp_number,
            notify_threshold=notify_threshold,
            display_threshold=display_threshold,
            token_hash=token_hash,
            hashed_password=hashed_password,
            quiet_hours_start=quiet_hours_start,
            quiet_hours_end=quiet_hours_end,
            timezone=timezone
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
        display_threshold: Optional[float] = None,
        quiet_hours_start: Optional[str] = None,
        quiet_hours_end: Optional[str] = None,
        timezone: Optional[str] = None
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
        if quiet_hours_start is not None:
            user.quiet_hours_start = quiet_hours_start
        if quiet_hours_end is not None:
            user.quiet_hours_end = quiet_hours_end
        if timezone is not None:
            user.timezone = timezone
        self.session.flush()
        return self._to_dict(user)

    def get_users_for_rotation(self, limit: int) -> List[Dict[str, Any]]:
        """
        Returns the `limit` users least-recently covered by a resume-driven
        keyword search, NULLs (never searched) first. Used by the scheduler's
        per-tick rotation so coverage is fair over time rather than always
        picking the same subset of users.
        """
        users = (
            self.session.query(UserORM)
            .order_by(UserORM.last_keyword_search_at.asc().nullsfirst())
            .limit(limit)
            .all()
        )
        return [self._to_dict(u) for u in users]

    def update_last_keyword_search(self, user_id: str) -> None:
        """Stamp the user as just covered by the keyword rotation."""
        user = self.session.query(UserORM).filter(UserORM.id == user_id).first()
        if user:
            user.last_keyword_search_at = datetime.now(timezone.utc)
            self.session.flush()

    def _to_dict(self, user: UserORM) -> Dict[str, Any]:
        return {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "whatsapp_number": user.whatsapp_number,
            "notify_threshold": user.notify_threshold,
            "display_threshold": user.display_threshold,
            "token_hash": user.token_hash,
            "hashed_password": user.hashed_password,
            "quiet_hours_start": user.quiet_hours_start,
            "quiet_hours_end": user.quiet_hours_end,
            "timezone": user.timezone,
            "created_at": user.created_at,
            "last_keyword_search_at": user.last_keyword_search_at,
        }

