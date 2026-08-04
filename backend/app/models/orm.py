import uuid
import json
from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, Integer, Boolean, Text, DateTime, ForeignKey, JSON, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from sqlalchemy.types import UserDefinedType
from app.database import Base

def generate_uuid():
    return str(uuid.uuid4())

def utcnow():
    return datetime.now(timezone.utc)


class VECTOR(UserDefinedType):
    """
    Custom SQLAlchemy type to support PostgreSQL pgvector's VECTOR type
    while falling back to JSON serialization for SQLite testing.
    """
    cache_ok = True

    def __init__(self, dim=384):
        self.dim = dim

    def get_col_spec(self, **kw):
        return f"VECTOR({self.dim})"

    def bind_processor(self, dialect):
        def process(value):
            if value is None:
                return None
            if dialect.name == "sqlite":
                return json.dumps(value)
            return value
        return process

    def result_processor(self, dialect, coltype):
        def process(value):
            if value is None:
                return None
            if dialect.name == "sqlite":
                return json.loads(value)
            if isinstance(value, str):
                try:
                    cleaned = value.strip("[]")
                    if cleaned:
                        return [float(x) for x in cleaned.split(",")]
                    return []
                except Exception:
                    return value
            return value
        return process

class UserORM(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    whatsapp_number = Column(String, nullable=True)
    notify_threshold = Column(Float, default=0.85, nullable=False)
    display_threshold = Column(Float, default=0.7, nullable=False)
    token_hash = Column(String, unique=True, index=True, nullable=True)
    hashed_password = Column(String, nullable=True)
    quiet_hours_start = Column(String, nullable=True)
    quiet_hours_end = Column(String, nullable=True)
    timezone = Column(String, nullable=True, default="Asia/Kolkata")
    created_at = Column(DateTime, default=utcnow)
    last_keyword_search_at = Column(DateTime, nullable=True)  # NULL = never searched; sorts first in rotation

    resumes = relationship("ResumeORM", back_populates="user", cascade="all, delete-orphan")
    resume_files = relationship("ResumeFileORM", back_populates="user", cascade="all, delete-orphan")
    applications = relationship("ApplicationORM", back_populates="user", cascade="all, delete-orphan")


class ResumeFileORM(Base):
    __tablename__ = "resume_files"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    resume_id = Column(String, ForeignKey("resumes.id", ondelete="SET NULL"), nullable=True)
    storage_provider = Column(String, default="cloudinary", nullable=False)
    storage_key = Column(String, nullable=False)
    filename = Column(String, nullable=False)
    content_type = Column(String, nullable=False)
    size_bytes = Column(Integer, nullable=False)
    sha256 = Column(String, nullable=False, index=True)
    processing_status = Column(String, default="pending", nullable=False)
    processing_attempts = Column(Integer, default=0, nullable=False)
    error_message = Column(Text, nullable=True)
    uploaded_at = Column(DateTime, default=utcnow, nullable=False)
    processed_at = Column(DateTime, nullable=True)
    extraction_method = Column(String, nullable=True)  # "text_layer" | "ocr" | "vision_ocr"

    user = relationship("UserORM", back_populates="resume_files")
    resume = relationship("ResumeORM", foreign_keys=[resume_id], uselist=False)


class ResumeORM(Base):
    __tablename__ = "resumes"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    raw_text = Column(Text, nullable=False)
    parsed_skills = Column(JSON, default=list, nullable=False)
    embedding = Column(VECTOR(384), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=utcnow)
    
    version = Column(Integer, default=1, nullable=False)
    parser_version = Column(String, nullable=True)
    resume_file_id = Column(String, ForeignKey("resume_files.id", ondelete="SET NULL"), nullable=True)

    user = relationship("UserORM", back_populates="resumes")
    resume_file = relationship("ResumeFileORM", foreign_keys=[resume_file_id], uselist=False)

    __table_args__ = (
        Index(
            'uq_active_resume_per_user',
            'user_id',
            unique=True,
            postgresql_where=(is_active == True),
            sqlite_where=(is_active == 1)
        ),
    )


class JobMatchORM(Base):
    __tablename__ = "job_matches"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    job_id = Column(String, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    score = Column(Float, nullable=False)
    rationale = Column(Text, nullable=True)
    status = Column(String, default="new", nullable=False)  # new, viewed, applied, dismissed
    notified_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utcnow)
    # Explainable sub-scores — populated by hybrid scorer (v2+). None for v1 (semantic only).
    score_breakdown = Column(JSON, nullable=True)
    # Scoring algorithm version — enables historical comparison across scoring formula changes.
    #   v1 = semantic-only (original cosine)
    #   v2 = hybrid (semantic + skill + title + experience)
    #   v3 = hybrid + LLM rerank
    scoring_version = Column(String, nullable=True, default="v1")

    __table_args__ = (
        UniqueConstraint("user_id", "job_id", name="uq_user_job_match"),
        Index("ix_job_matches_user_score_created", "user_id", "score", "created_at"),
    )



class EmbeddingCacheORM(Base):
    __tablename__ = "embedding_cache"

    id = Column(String, primary_key=True, default=generate_uuid)
    entity_type = Column(String, nullable=False, index=True)  # e.g. "resume", "job", "company"
    entity_id = Column(String, nullable=False, index=True)
    section = Column(String, nullable=False, default="primary")  # e.g. "skills", "projects", "experience"
    embedding = Column(JSON, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)



class CompanyORM(Base):
    __tablename__ = "companies"

    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False, index=True)
    website = Column(String, nullable=True)
    industry = Column(String, nullable=True)
    logo_url = Column(String, nullable=True)
    career_url = Column(String, nullable=True, index=True)
    created_at = Column(DateTime, default=utcnow)

    jobs = relationship("JobORM", back_populates="company", cascade="all, delete-orphan")


class JobORM(Base):
    __tablename__ = "jobs"

    id = Column(String, primary_key=True, default=generate_uuid)
    company_id = Column(String, ForeignKey("companies.id"), nullable=True, index=True)
    title = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=False)
    url = Column(String, unique=True, index=True, nullable=False)
    location = Column(String, nullable=True)
    employment_type = Column(String, nullable=True)
    salary = Column(String, nullable=True)
    salary_currency = Column(String, nullable=True)
    remote = Column(Boolean, nullable=True)
    seniority = Column(String, nullable=True)
    experience_required = Column(Float, nullable=True)
    posted_date = Column(String, nullable=True)
    source = Column(String, nullable=True)
    embedding = Column(VECTOR(384), nullable=True)
    created_at = Column(DateTime, default=utcnow)
    last_seen_at = Column(DateTime, default=utcnow, nullable=True)
    # ---------------------------------------------------------------------------
    # Structured fields — derived deterministically by job_parser during embedding.
    # Source of truth is always the raw job description; reprocessing regenerates
    # these fields. Do not allow manual edits.
    # ---------------------------------------------------------------------------
    required_skills  = Column(JSON,   nullable=True)   # List[str] extracted before "nice to have" markers
    preferred_skills = Column(JSON,   nullable=True)   # List[str] extracted after those markers
    normalized_title = Column(String, nullable=True)   # canonical title slug e.g. "frontend_engineer"
    # Tracks which job_parser version produced the structured fields above.
    # Allows identifying stale records when parser logic improves.
    #   v1 = SkillExtractor + ExperienceExtractor + TitleNormalizer + SeniorityDetector (initial)
    job_parser_version = Column(String, nullable=True)

    company = relationship("CompanyORM", back_populates="jobs")


class ApplicationORM(Base):
    __tablename__ = "applications"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    job_id = Column(String, ForeignKey("jobs.id"), nullable=False, index=True)
    resume_id = Column(String, ForeignKey("resumes.id", ondelete="SET NULL"), nullable=True, index=True)  # Resume snapshot for gap report versioning
    status = Column(String, default="Saved")  # Saved, Applied, Assessment, OA, Interview, Offer, Rejected, Withdrawn
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    user = relationship("UserORM", back_populates="applications")
    notes_list = relationship("InterviewNoteORM", back_populates="application", cascade="all, delete-orphan")


class GapReportORM(Base):
    __tablename__ = "gap_reports"

    id = Column(String, primary_key=True, default=generate_uuid)
    job_id = Column(String, ForeignKey("jobs.id"), nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    resume_version = Column(Integer, default=1)
    confidence_score = Column(Float, nullable=True)
    overall_summary = Column(Text, nullable=False)
    report_data = Column(JSON, nullable=True)
    generated_at = Column(DateTime, default=utcnow)


class JobSourceORM(Base):
    __tablename__ = "job_sources"

    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False, index=True)
    url = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    last_fetched_at = Column(DateTime, nullable=True)
    poll_interval_minutes = Column(Integer, nullable=True, default=60)



class InterviewNoteORM(Base):
    __tablename__ = "interview_notes"

    id = Column(String, primary_key=True, default=generate_uuid)
    application_id = Column(String, ForeignKey("applications.id"), nullable=False, index=True)
    note = Column(Text, nullable=False)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, nullable=True, onupdate=utcnow)

    application = relationship("ApplicationORM", back_populates="notes_list")


class IngestionRunORM(Base):
    __tablename__ = "ingestion_runs"

    id = Column(String, primary_key=True, default=generate_uuid)
    started_at = Column(DateTime, default=utcnow, index=True)
    completed_at = Column(DateTime, nullable=True)
    source = Column(String, nullable=False, index=True)
    jobs_fetched = Column(Integer, default=0)
    jobs_inserted = Column(Integer, default=0)
    jobs_updated = Column(Integer, default=0)
    duplicates_removed = Column(Integer, default=0)
    failures = Column(Integer, default=0)
    duration_ms = Column(Float, default=0.0)
    status = Column(String, default="Running")  # Running, Success, Failed, Partial

