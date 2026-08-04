import logging
import json
import httpx
import redis
from datetime import datetime
from app.repositories.uow import UnitOfWork
from app.services.storage.cloudinary_client import get_signed_download_url
from app.services.resume_processing.text_extraction import extract_text_pdf, extract_text_docx
from app.services.resume_processing.parse_resume import parse_resume_text
from app.services.scoring_service import scoring_service
from app.config import settings

logger = logging.getLogger(__name__)

def process_resume_file(resume_file_id: str, user_id: str) -> None:
    """
    Background worker task to extract, parse, save, and score an uploaded resume.
    Ensures safe circular foreign key updates:
    1. Mark status as "processing" in resume_files.
    2. Extract & Parse resume.
    3. Create/Upsert active resumes row with resume_file_id linked.
    4. Rescore all database jobs against the new resume embedding in the background.
    5. Update resume_files.resume_id to point to resumes.id and mark complete.
    6. Send real-time SSE updates.
    """
    logger.info(f"Starting background processing for resume file {resume_file_id} (user {user_id})")

    # 1. Mark processing and increment attempt count
    with UnitOfWork() as uow:
        try:
            resume_file = uow.resume_files.mark_processing(resume_file_id)
            uow.commit()
        except Exception as e:
            logger.error(f"Failed to mark resume file {resume_file_id} as processing: {e}")
            return

    try:
        # 2. Retrieve download URL and fetch file bytes
        public_id = resume_file["storage_key"]
        signed_url = get_signed_download_url(public_id)

        logger.info(f"Downloading file from Cloudinary (signed URL expires in 300s)")
        resp = httpx.get(signed_url, timeout=30.0)
        if resp.status_code != 200:
            raise RuntimeError(f"Failed to download file from Cloudinary (HTTP {resp.status_code})")
        file_bytes = resp.content

        # 3. Extract plain text
        filename = resume_file["filename"]
        ext = filename.lower().split(".")[-1] if "." in filename else ""
        if ext == "pdf":
            raw_text, extraction_method = extract_text_pdf(file_bytes)
        elif ext == "docx":
            raw_text = extract_text_docx(file_bytes)
            extraction_method = "text_layer"  # DOCX always has a real text layer
        else:
            raise ValueError(f"Unsupported file type for extraction: {ext}")

        if not raw_text.strip():
            raise ValueError("Extracted text is empty. The file may be scanned, image-only, or empty.")

        # 4. Parse raw text into structured fields (LLM with heuristic fallback)
        parsed_profile, parser_version = parse_resume_text(raw_text)

        # 5. Create/Upsert the active resumes record
        with UnitOfWork() as uow:
            # Determine max version to increment next active version row
            from app.models.orm import ResumeORM
            from sqlalchemy import func
            max_ver = uow.session.query(func.max(ResumeORM.version)).filter(ResumeORM.user_id == user_id).scalar() or 0
            next_ver = max_ver + 1

            resume_dict = uow.resumes.upsert_resume(
                user_id=user_id,
                title=parsed_profile.title,
                years_experience=parsed_profile.years_experience,
                skills=parsed_profile.skills,
                projects=[p.dict() for p in parsed_profile.projects],
                resume_file_id=resume_file_id,
                version=next_ver,
                parser_version=parser_version,
                raw_text=raw_text
            )
            uow.commit()

        # 6. Recalculate match scores for all database jobs against the new embedding
        # This suppresses individual SSE matches and runs with isolated try-excepts per job.
        try:
            scoring_service.score_all_jobs_for_user(user_id)
        except Exception as es:
            logger.error(f"Error rescoring jobs during resume processing for user {user_id}: {es}", exc_info=True)

        # 7. Complete the circle: update resume_files with the resume_id link and mark complete
        with UnitOfWork() as uow:
            uow.resume_files.mark_complete(resume_file_id, resume_dict["id"], extraction_method)
            uow.commit()

        logger.info(f"Successfully processed resume file {resume_file_id} (user {user_id}). Version: {next_ver}.")

        # 8. Publish successful SSE event
        _publish_sse_event(user_id, {
            "type": "resume_processed",
            "status": "complete",
            "resume_file_id": resume_file_id,
            "resume_id": resume_dict["id"],
            "filename": filename
        })

    except Exception as e:
        logger.error(f"Error during processing of resume file {resume_file_id}: {e}", exc_info=True)
        
        # Mark as failed (respecting retry limit)
        with UnitOfWork() as uow:
            updated_file = uow.resume_files.mark_failed(
                resume_file_id, str(e), settings.resume_processing_max_retries
            )
            uow.commit()

        # Publish failed SSE event
        retryable = updated_file["processing_status"] == "pending"
        _publish_sse_event(user_id, {
            "type": "resume_processed",
            "status": "failed",
            "resume_file_id": resume_file_id,
            "filename": resume_file["filename"],
            "retryable": retryable,
            "error_message": str(e)
        })

def _publish_sse_event(user_id: str, payload: dict) -> None:
    """Publishes progress events to Redis PubSub."""
    try:
        from app.redis_client import get_redis_client
        client = get_redis_client()
        client.publish(f"job_events:{user_id}", json.dumps(payload))
        logger.info(f"Published resume SSE event to channel job_events:{user_id}")
    except Exception as e:
        logger.warning(f"Could not publish resume status SSE for {user_id}: {e}")

