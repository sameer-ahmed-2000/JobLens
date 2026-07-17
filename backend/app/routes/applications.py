"""
Career Workspace — Applications & Interview Notes API
"""
import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel
from app.repositories.uow import UnitOfWork
from app.routes.auth import get_current_user_id
from app.models.orm import InterviewNoteORM

logger = logging.getLogger("applications_api")
router = APIRouter()


# ─────────────────────────────────────────────────────────
# Pydantic request / response schemas
# ─────────────────────────────────────────────────────────

class SaveApplicationRequest(BaseModel):
    job_id: str


class UpdateStatusRequest(BaseModel):
    status: str


class AddNoteRequest(BaseModel):
    content: str


class UpdateNoteRequest(BaseModel):
    content: str


# ─────────────────────────────────────────────────────────
# Applications endpoints
# ─────────────────────────────────────────────────────────

@router.get("/applications")
def list_applications(current_user_id: str = Depends(get_current_user_id)):
    """Return all applications for the current user, enriched with job + score data."""
    with UnitOfWork() as uow:
        return uow.applications.list_applications(current_user_id)


@router.post("/applications", status_code=status.HTTP_201_CREATED)
def save_application(req: SaveApplicationRequest, current_user_id: str = Depends(get_current_user_id)):
    """
    Save a job to the application tracker for the current user.
    Returns 409 if already saved.
    """
    with UnitOfWork() as uow:
        # Check for duplicate
        if uow.applications.application_exists(current_user_id, req.job_id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Application already exists for this job.",
            )

        # Capture the current resume_id for snapshot
        resume_id: Optional[str] = None
        try:
            res = uow.resumes.get_by_user_id(current_user_id)
            if res:
                resume_id = res.get("id")
        except Exception:
            pass  # resume snapshot is optional

        try:
            app = uow.applications.save_application(
                user_id=current_user_id,
                job_id=req.job_id,
                resume_id=resume_id,
            )
            uow.commit()
            return app
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
        except Exception as e:
            logger.error(f"Save application error: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Failed to save application.")


@router.patch("/applications/{app_id}")
def update_application_status(app_id: str, req: UpdateStatusRequest, current_user_id: str = Depends(get_current_user_id)):
    """Update the status of an application after verifying ownership."""
    with UnitOfWork() as uow:
        app = uow.applications.get_application(app_id)
        if not app or app["user_id"] != current_user_id:
            raise HTTPException(status_code=404, detail="Application not found.")

        try:
            result = uow.applications.update_status(app_id, req.status)
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

        if result is None:
            raise HTTPException(status_code=404, detail="Application not found.")

        uow.commit()
        return result


@router.delete("/applications/{app_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_application(app_id: str, current_user_id: str = Depends(get_current_user_id)):
    """Permanently delete an application and all its notes after verifying ownership."""
    with UnitOfWork() as uow:
        app = uow.applications.get_application(app_id)
        if not app or app["user_id"] != current_user_id:
            raise HTTPException(status_code=404, detail="Application not found.")

        deleted = uow.applications.delete_application(app_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Application not found.")
        uow.commit()


@router.get("/applications/{app_id}")
def get_application(app_id: str, current_user_id: str = Depends(get_current_user_id)):
    """Get a single application by ID after verifying ownership."""
    with UnitOfWork() as uow:
        app = uow.applications.get_application(app_id)
        if not app or app["user_id"] != current_user_id:
            raise HTTPException(status_code=404, detail="Application not found.")
        return app


# ─────────────────────────────────────────────────────────
# Check if a job is already saved (used by UI to show ✓ Saved)
# ─────────────────────────────────────────────────────────

@router.get("/applications/check/{job_id}")
def check_application_exists(job_id: str, current_user_id: str = Depends(get_current_user_id)):
    """Returns whether a job is already saved, and the application if so."""
    with UnitOfWork() as uow:
        app = uow.applications.get_by_job(current_user_id, job_id)
        return {"exists": app is not None, "application": app}


# ─────────────────────────────────────────────────────────
# Interview Notes sub-resource
# ─────────────────────────────────────────────────────────

@router.get("/applications/{app_id}/notes")
def get_notes(app_id: str, current_user_id: str = Depends(get_current_user_id)):
    """List all interview notes for an application after verifying ownership."""
    with UnitOfWork() as uow:
        app = uow.applications.get_application(app_id)
        if not app or app["user_id"] != current_user_id:
            raise HTTPException(status_code=404, detail="Application not found.")
        return uow.interview_notes.get_notes(app_id)


@router.post("/applications/{app_id}/notes", status_code=status.HTTP_201_CREATED)
def add_note(app_id: str, req: AddNoteRequest, current_user_id: str = Depends(get_current_user_id)):
    """Add an interview note to an application after verifying ownership."""
    with UnitOfWork() as uow:
        app = uow.applications.get_application(app_id)
        if not app or app["user_id"] != current_user_id:
            raise HTTPException(status_code=404, detail="Application not found.")
        if not req.content or not req.content.strip():
            raise HTTPException(status_code=400, detail="Note content cannot be empty.")
        note = uow.interview_notes.add_note(app_id, req.content.strip())
        uow.commit()
        return note


@router.patch("/notes/{note_id}")
def update_note(note_id: str, req: UpdateNoteRequest, current_user_id: str = Depends(get_current_user_id)):
    """Edit an interview note after verifying ownership of the parent application."""
    with UnitOfWork() as uow:
        note = uow.session.query(InterviewNoteORM).filter(InterviewNoteORM.id == note_id).first()
        if not note:
            raise HTTPException(status_code=404, detail="Note not found.")
        app = uow.applications.get_application(note.application_id)
        if not app or app["user_id"] != current_user_id:
            raise HTTPException(status_code=404, detail="Note not found.")

        if not req.content or not req.content.strip():
            raise HTTPException(status_code=400, detail="Note content cannot be empty.")
        
        updated_note = uow.interview_notes.update_note(note_id, req.content.strip())
        uow.commit()
        return updated_note


@router.delete("/notes/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_note(note_id: str, current_user_id: str = Depends(get_current_user_id)):
    """Delete an interview note after verifying ownership of the parent application."""
    with UnitOfWork() as uow:
        note = uow.session.query(InterviewNoteORM).filter(InterviewNoteORM.id == note_id).first()
        if not note:
            raise HTTPException(status_code=404, detail="Note not found.")
        app = uow.applications.get_application(note.application_id)
        if not app or app["user_id"] != current_user_id:
            raise HTTPException(status_code=404, detail="Note not found.")

        deleted = uow.interview_notes.delete_note(note_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Note not found.")
        uow.commit()
