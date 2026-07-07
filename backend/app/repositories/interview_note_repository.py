from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.orm import InterviewNoteORM


class InterviewNoteRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_notes(self, application_id: str) -> List[Dict[str, Any]]:
        notes = (
            self.session.query(InterviewNoteORM)
            .filter(InterviewNoteORM.application_id == application_id)
            .order_by(InterviewNoteORM.created_at.asc())
            .all()
        )
        return [self._to_dict(n) for n in notes]

    def add_note(self, application_id: str, content: str) -> Dict[str, Any]:
        note = InterviewNoteORM(
            application_id=application_id,
            note=content,
            created_at=datetime.utcnow(),
        )
        self.session.add(note)
        self.session.flush()
        return self._to_dict(note)

    def update_note(self, note_id: str, content: str) -> Optional[Dict[str, Any]]:
        note = self.session.query(InterviewNoteORM).filter(InterviewNoteORM.id == note_id).first()
        if not note:
            return None
        note.note = content
        note.updated_at = datetime.utcnow()
        self.session.flush()
        return self._to_dict(note)

    def delete_note(self, note_id: str) -> bool:
        note = self.session.query(InterviewNoteORM).filter(InterviewNoteORM.id == note_id).first()
        if not note:
            return False
        self.session.delete(note)
        self.session.flush()
        return True

    def _to_dict(self, note: InterviewNoteORM) -> Dict[str, Any]:
        return {
            "id": note.id,
            "application_id": note.application_id,
            "content": note.note,
            "created_at": note.created_at,
            "updated_at": getattr(note, "updated_at", None),
        }
