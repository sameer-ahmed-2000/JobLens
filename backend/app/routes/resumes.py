import hashlib
import logging
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, UploadFile, File
from fastapi.responses import JSONResponse

from app.routes.auth import get_current_user_id

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/resume/upload")
async def upload_resume(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    current_user_id: str = Depends(get_current_user_id)
):
    """
    Validates the resume file, stores it privately on Cloudinary (or mock storage),
    and triggers async text extraction & parsing.
    Returns 202 Accepted.
    """
    from app.services.resume_processing.validation import validate_resume_file
    from app.services.storage.cloudinary_client import upload_resume_file, CloudinaryConfigError
    from app.services.resume_processing.processor import process_resume_file
    from app.repositories.uow import UnitOfWork

    # 1. Read bytes
    file_bytes = await file.read()

    # 2. Validate file
    try:
        validate_resume_file(file_bytes, file.filename)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # 3. Calculate SHA256
    sha256 = hashlib.sha256(file_bytes).hexdigest()

    # 4. Duplicate lookup (scoped to non-failed rows)
    storage_key = None
    with UnitOfWork() as uow:
        existing = uow.resume_files.get_by_sha256(current_user_id, sha256)
        if existing:
            storage_key = existing["storage_key"]

    # 5. Upload to Cloudinary if not reused
    if not storage_key:
        try:
            upload_result = upload_resume_file(file_bytes, file.filename, current_user_id)
            storage_key = upload_result["public_id"]
        except CloudinaryConfigError as cce:
            raise HTTPException(status_code=503, detail=str(cce))
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to upload resume to storage: {str(e)}")

    # 6. Create resume_files database record
    with UnitOfWork() as uow:
        file_rec = uow.resume_files.create(
            user_id=current_user_id,
            storage_key=storage_key,
            filename=file.filename,
            content_type=file.content_type,
            size_bytes=len(file_bytes),
            sha256=sha256
        )
        uow.commit()

    # 7. Dispatch background worker task
    background_tasks.add_task(process_resume_file, file_rec["id"], current_user_id)

    return JSONResponse(
        status_code=202,
        content={
            "resume_file_id": file_rec["id"],
            "status": "pending",
            "message": "Resume uploaded successfully. Processing in background -- updates will stream live."
        }
    )


@router.get("/resume/status")
async def get_latest_resume_status(current_user_id: str = Depends(get_current_user_id)):
    """Retrieve details of the user's latest uploaded resume file."""
    from app.repositories.uow import UnitOfWork
    with UnitOfWork() as uow:
        statuses = uow.resume_files.get_status_for_user(current_user_id)
        if not statuses:
            return None
        return statuses[0]


@router.get("/resume/status/{resume_file_id}")
async def get_resume_status(
    resume_file_id: str,
    current_user_id: str = Depends(get_current_user_id)
):
    """Retrieve details of a specific resume file. Ownership-checked (404 on mismatch)."""
    from app.repositories.uow import UnitOfWork
    with UnitOfWork() as uow:
        rec = uow.resume_files.get(resume_file_id)
        if not rec or rec["user_id"] != current_user_id:
            raise HTTPException(status_code=404, detail="Resume file not found.")
        return rec


@router.post("/resume/{resume_file_id}/reprocess")
async def reprocess_resume(
    resume_file_id: str,
    background_tasks: BackgroundTasks,
    current_user_id: str = Depends(get_current_user_id)
):
    """Reprocess an already uploaded resume file. Ownership-checked (404 on mismatch)."""
    from app.repositories.uow import UnitOfWork
    from app.services.resume_processing.processor import process_resume_file

    with UnitOfWork() as uow:
        rec = uow.resume_files.get(resume_file_id)
        if not rec or rec["user_id"] != current_user_id:
            raise HTTPException(status_code=404, detail="Resume file not found.")

        # Reset attempts & status to pending
        uow.resume_files.reset_attempts(resume_file_id)
        uow.commit()

    background_tasks.add_task(process_resume_file, resume_file_id, current_user_id)
    return {"status": "pending", "message": "Reprocessing started in the background."}


@router.get("/resume/{resume_id}/download")
async def download_resume(
    resume_id: str,
    current_user_id: str = Depends(get_current_user_id)
):
    """Generates a secure signed Cloudinary download URL for a resume version. Ownership-checked (404 on mismatch)."""
    from app.repositories.uow import UnitOfWork
    from app.services.storage.cloudinary_client import get_signed_download_url, CloudinaryConfigError

    with UnitOfWork() as uow:
        resume = uow.resumes.get_by_id(resume_id)
        if not resume or resume["user_id"] != current_user_id:
            raise HTTPException(status_code=404, detail="Resume not found.")

        file_id = resume.get("resume_file_id")
        if not file_id:
            raise HTTPException(status_code=404, detail="No source document associated with this resume version.")

        rec = uow.resume_files.get(file_id)
        if not rec or rec["user_id"] != current_user_id:
            raise HTTPException(status_code=404, detail="Source document not found.")

        try:
            url = get_signed_download_url(rec["storage_key"])
            return {"url": url}
        except CloudinaryConfigError as cce:
            raise HTTPException(status_code=503, detail=str(cce))
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to generate download URL: {str(e)}")


@router.get("/resume/active")
async def get_active_resume(current_user_id: str = Depends(get_current_user_id)):
    """Retrieve the current active resume profile (parsed details) for the user."""
    from app.repositories.uow import UnitOfWork
    with UnitOfWork() as uow:
        resume = uow.resumes.get_active(current_user_id)
        if not resume:
            raise HTTPException(status_code=404, detail="No active resume profile found.")
        return resume
