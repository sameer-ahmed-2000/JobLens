import pytest
import hashlib
from datetime import datetime
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import Base
from app.repositories.uow import UnitOfWork
from app.models.orm import UserORM, ResumeORM, ResumeFileORM, JobORM
from app.services.resume_processing.validation import validate_resume_file
from app.services.storage.cloudinary_client import upload_resume_file, get_signed_download_url, CloudinaryConfigError

import os

# Setup test DB (SQLite file-based)
test_engine = create_engine("sqlite:///test_resume_upload.db", connect_args={"check_same_thread": False})
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

class SQLiteUnitOfWork(UnitOfWork):
    def __init__(self):
        super().__init__(session_factory=TestSessionLocal)

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_database():
    import app.database
    import app.repositories.uow
    orig_db_sl = getattr(app.database, "SessionLocal", None)
    orig_uow_sl = getattr(app.repositories.uow, "SessionLocal", None)
    app.database.SessionLocal = TestSessionLocal
    app.repositories.uow.SessionLocal = TestSessionLocal

    Base.metadata.create_all(bind=test_engine)
    
    # Create default test user
    with SQLiteUnitOfWork() as uow:
        # Create a user with a token that resolves to user-123
        user = UserORM(
            id="user-123",
            name="Test User",
            email="testuser@example.com",
            token_hash=hashlib.sha256("test-token".encode("utf-8")).hexdigest(),
            display_threshold=0.7,
            notify_threshold=0.8
        )
        uow.session.add(user)
        uow.commit()

    yield
    # Cleanup Session overrides
    if orig_db_sl:
        app.database.SessionLocal = orig_db_sl
    if orig_uow_sl:
        app.repositories.uow.SessionLocal = orig_uow_sl

    # Close test connection pool and delete file-based database
    test_engine.dispose()
    if os.path.exists("test_resume_upload.db"):
        try:
            os.remove("test_resume_upload.db")
        except Exception:
            pass


# 1. Validation Tests
def test_validation_size_limit():
    with patch("app.services.resume_processing.validation.settings") as mock_settings:
        mock_settings.resume_max_size_mb = 1  # 1MB limit
        large_bytes = b"0" * (2 * 1024 * 1024)  # 2MB
        with pytest.raises(ValueError, match="File size exceeds"):
            validate_resume_file(large_bytes, "test.pdf")

def test_validation_extension():
    with pytest.raises(ValueError, match="Unsupported file extension"):
        validate_resume_file(b"some content", "test.txt")

def test_validation_magic_bytes_pdf():
    with pytest.raises(ValueError, match="File content does not match PDF signature"):
        validate_resume_file(b"not a pdf", "test.pdf")

def test_validation_magic_bytes_docx():
    with pytest.raises(ValueError, match="File content does not match DOCX signature"):
        validate_resume_file(b"not a docx", "test.docx")

# 2. Cloudinary Production Configuration Gating
def test_cloudinary_gating_production():
    with patch("app.services.storage.cloudinary_client.is_test_env", False), \
         patch("app.services.storage.cloudinary_client.has_credentials", False):
        with pytest.raises(CloudinaryConfigError, match="Cloudinary credentials are not configured"):
            upload_resume_file(b"%PDF-1.4", "test.pdf", "user-123")

# 3. Ownership Validation
def test_ownership_validation():
    # Insert a resume file owned by a different user
    with SQLiteUnitOfWork() as uow:
        other_user = UserORM(id="other-user", name="Other", email="other@example.com")
        uow.session.add(other_user)
        
        file_rec = ResumeFileORM(
            id="file-other",
            user_id="other-user",
            storage_provider="cloudinary",
            storage_key="key-other",
            filename="other.pdf",
            content_type="application/pdf",
            size_bytes=100,
            sha256="abc"
        )
        uow.session.add(file_rec)
        
        resume_rec = ResumeORM(
            id="resume-other",
            user_id="other-user",
            raw_text="Other resume text",
            embedding=[0.0]*384,
            resume_file_id="file-other"
        )
        uow.session.add(resume_rec)
        uow.commit()

    headers = {"Authorization": "Bearer test-token"}
    
    # Try to access status of other user's file
    res = client.get("/api/resume/status/file-other", headers=headers)
    assert res.status_code == 404

    # Try to reprocess other user's file
    res = client.post("/api/resume/file-other/reprocess", headers=headers)
    assert res.status_code == 404

    # Try to download other user's resume
    res = client.get("/api/resume/resume-other/download", headers=headers)
    assert res.status_code == 404

# 4. SHA256 Duplicate Check
def test_sha256_duplicate_upload():
    headers = {"Authorization": "Bearer test-token"}
    pdf_content = b"%PDF-1.4 test content"
    
    with patch("app.services.storage.cloudinary_client.upload_resume_file") as mock_upload, \
         patch("app.services.resume_processing.processor.process_resume_file") as mock_process:
        
        mock_upload.return_value = {"public_id": "test_public_id", "secure_url": "http://cloudinary/test_public_id"}
        
        res1 = client.post(
            "/api/resume/upload",
            headers=headers,
            files={"file": ("test.pdf", pdf_content, "application/pdf")}
        )
        assert res1.status_code == 202
        assert mock_upload.call_count == 1
        
        # Second upload with identical bytes
        res2 = client.post(
            "/api/resume/upload",
            headers=headers,
            files={"file": ("test.pdf", pdf_content, "application/pdf")}
        )
        assert res2.status_code == 202
        # Mock upload should NOT be called again since SHA256 matches and is reused
        assert mock_upload.call_count == 1
        
        # Check database: we should have two different resume_files rows
        with SQLiteUnitOfWork() as uow:
            files = uow.session.query(ResumeFileORM).filter(ResumeFileORM.user_id == "user-123").all()
            assert len(files) == 2
            assert files[0].storage_key == "test_public_id"
            assert files[1].storage_key == "test_public_id"
            assert files[0].id != files[1].id

# 5. Background rescoring and try/except isolation
def test_isolated_scoring_failure():
    # Setup database with some jobs, one having corrupted embedding representation
    with SQLiteUnitOfWork() as uow:
        job1 = JobORM(id="job-1", title="AI Engineer", description="desc", url="url1", embedding=[0.1]*384)
        job2 = JobORM(id="job-2", title="Web Engineer", description="desc", url="url2", embedding="corrupted_embedding")
        job3 = JobORM(id="job-3", title="Data Scientist", description="desc", url="url3", embedding=[0.2]*384)
        uow.session.add_all([job1, job2, job3])
        uow.commit()

    from app.services.scoring_service import scoring_service
    
    # We trigger a rescore for the user. We patch the cache to return a dummy embedding
    with patch.object(scoring_service.cache, "get_all") as mock_cache:
        mock_cache.return_value = {
            "user-123": {
                "embedding": [0.1]*384,
                "display_threshold": 0.5,
                "notify_threshold": 0.8
            }
        }
        
        # Execute rescore. It should successfully score job-1 and job-3, skipping job-2, without throwing an error
        scoring_service.score_all_jobs_for_user("user-123")
        
        # Verify job matches created for job-1 and job-3
        with SQLiteUnitOfWork() as uow:
            from app.models.orm import JobMatchORM
            db_matches = uow.session.query(JobMatchORM).filter(JobMatchORM.user_id == "user-123").all()
            assert len(db_matches) == 2
            job_ids = {m.job_id for m in db_matches}
            assert "job-1" in job_ids
            assert "job-3" in job_ids
            assert "job-2" not in job_ids


# 6. Active Resume Fetch
def test_get_active_resume():
    headers = {"Authorization": "Bearer test-token"}
    
    # 404 if no resume
    res = client.get("/api/resume/active", headers=headers)
    assert res.status_code == 404
    
    # Create an active resume
    with SQLiteUnitOfWork() as uow:
        resume = ResumeORM(
            id="active-resume-id",
            user_id="user-123",
            raw_text="Extracted text here",
            parsed_skills=["Python", "SQL"],
            embedding=[0.05]*384,
            is_active=True
        )
        uow.session.add(resume)
        uow.commit()
        
    res = client.get("/api/resume/active", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == "active-resume-id"
    assert data["skills"] == ["Python", "SQL"]
    assert data["raw_text"] == "Extracted text here"

