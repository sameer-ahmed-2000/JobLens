from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

from sqlalchemy.orm import Session
from app.models.orm import ResumeFileORM

class ResumeFileRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(
        self,
        user_id: str,
        storage_key: str,
        filename: str,
        content_type: str,
        size_bytes: int,
        sha256: str
    ) -> Dict[str, Any]:
        """
        Creates a new resume file record with pending status.
        """
        row = ResumeFileORM(
            user_id=user_id,
            storage_key=storage_key,
            filename=filename,
            content_type=content_type,
            size_bytes=size_bytes,
            sha256=sha256,
            processing_status="pending",
            processing_attempts=0
        )
        self.session.add(row)
        self.session.flush()
        return self._to_dict(row)

    def get(self, file_id: str) -> Optional[Dict[str, Any]]:
        row = self.session.query(ResumeFileORM).filter(ResumeFileORM.id == file_id).first()
        if not row:
            return None
        return self._to_dict(row)

    def get_by_sha256(self, user_id: str, sha256: str) -> Optional[Dict[str, Any]]:
        """
        Finds an existing successful or pending upload for this user with matching SHA256.
        Excludes failed processing rows to allow retrying uploads.
        """
        row = self.session.query(ResumeFileORM).filter(
            ResumeFileORM.user_id == user_id,
            ResumeFileORM.sha256 == sha256,
            ResumeFileORM.processing_status != "failed"
        ).first()
        if not row:
            return None
        return self._to_dict(row)

    def mark_processing(self, file_id: str) -> Dict[str, Any]:
        row = self.session.query(ResumeFileORM).filter(ResumeFileORM.id == file_id).first()
        if not row:
            raise ValueError(f"ResumeFile record not found: {file_id}")
        row.processing_status = "processing"
        row.processing_attempts += 1
        self.session.flush()
        return self._to_dict(row)

    def mark_complete(self, file_id: str, resume_id: str) -> Dict[str, Any]:
        row = self.session.query(ResumeFileORM).filter(ResumeFileORM.id == file_id).first()
        if not row:
            raise ValueError(f"ResumeFile record not found: {file_id}")
        row.processing_status = "complete"
        row.resume_id = resume_id
        row.processed_at = datetime.now(timezone.utc)
        row.error_message = None

        self.session.flush()
        return self._to_dict(row)

    def mark_failed(self, file_id: str, error_message: str, max_retries: int) -> Dict[str, Any]:
        row = self.session.query(ResumeFileORM).filter(ResumeFileORM.id == file_id).first()
        if not row:
            raise ValueError(f"ResumeFile record not found: {file_id}")
        row.error_message = error_message
        row.processing_status = "failed"
            
        self.session.flush()
        return self._to_dict(row)

    def reset_attempts(self, file_id: str) -> None:
        """
        Resets attempt count to zero and sets status to pending so it can be reprocessed.
        """
        row = self.session.query(ResumeFileORM).filter(ResumeFileORM.id == file_id).first()
        if row:
            row.processing_attempts = 0
            row.processing_status = "pending"
            row.error_message = None
            self.session.flush()

    def get_status_for_user(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Fetches chronological uploads list for a user.
        """
        rows = self.session.query(ResumeFileORM).filter(
            ResumeFileORM.user_id == user_id
        ).order_by(ResumeFileORM.uploaded_at.desc()).all()
        return [self._to_dict(r) for r in rows]

    def _to_dict(self, row: ResumeFileORM) -> Dict[str, Any]:
        return {
            "id": row.id,
            "user_id": row.user_id,
            "resume_id": row.resume_id,
            "storage_provider": row.storage_provider,
            "storage_key": row.storage_key,
            "filename": row.filename,
            "content_type": row.content_type,
            "size_bytes": row.size_bytes,
            "sha256": row.sha256,
            "processing_status": row.processing_status,
            "processing_attempts": row.processing_attempts,
            "error_message": row.error_message,
            "uploaded_at": row.uploaded_at,
            "processed_at": row.processed_at
        }
