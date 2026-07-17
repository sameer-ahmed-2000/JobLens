import uuid
import json
from datetime import datetime
from sqlalchemy import Column, String, Float, Integer, Boolean, Text, DateTime, ForeignKey, JSON, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from sqlalchemy.types import UserDefinedType
from app.database import Base

def generate_uuid():
    return str(uuid.uuid4())

class VECTOR(UserDefinedType):
    """
    Custom SQLAlchemy type to support PostgreSQL pgvector's VECTOR type
    while falling back to JSON serialization for SQLite testing.
    """
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
    created_at = Column(DateTime, default=datetime.utcnow)

    resumes = relationship("ResumeORM", back_populates="user", cascade="all, delete-orphan")
    applications = relationship("ApplicationORM", back_populates="user", cascade="all, delete-orphan")


class ResumeORM(Base):
    __tablename__ = "resumes"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    raw_text = Column(Text, nullable=False)
    parsed_skills = Column(JSON, default=list, nullable=False)
    embedding = Column(VECTOR(384), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("UserORM", back_populates="resumes")

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
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("user_id", "job_id", name="uq_user_job_match"),
    )


class EmbeddingCacheORM(Base):
    __tablename__ = "embedding_cache"

    id = Column(String, primary_key=True, default=generate_uuid)
    entity_type = Column(String, nullable=False, index=True)  # e.g. "resume", "job", "company"
    entity_id = Column(String, nullable=False, index=True)
    section = Column(String, nullable=False, default="primary")  # e.g. "skills", "projects", "experience"
    embedding = Column(JSON, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)



class CompanyORM(Base):
    __tablename__ = "companies"

    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False, index=True)
    website = Column(String, nullable=True)
    industry = Column(String, nullable=True)
    logo_url = Column(String, nullable=True)
    career_url = Column(String, nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

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
    embedding = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    company = relationship("CompanyORM", back_populates="jobs")


class ApplicationORM(Base):
    __tablename__ = "applications"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    job_id = Column(String, ForeignKey("jobs.id"), nullable=False, index=True)
    resume_id = Column(String, ForeignKey("resumes.id"), nullable=True, index=True)  # Resume snapshot for gap report versioning
    status = Column(String, default="Saved")  # Saved, Applied, Assessment, OA, Interview, Offer, Rejected, Withdrawn
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

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
    generated_at = Column(DateTime, default=datetime.utcnow)


class JobSourceORM(Base):
    __tablename__ = "job_sources"

    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False, index=True)
    url = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    last_fetched_at = Column(DateTime, nullable=True)


class InterviewNoteORM(Base):
    __tablename__ = "interview_notes"

    id = Column(String, primary_key=True, default=generate_uuid)
    application_id = Column(String, ForeignKey("applications.id"), nullable=False, index=True)
    note = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=True, onupdate=datetime.utcnow)

    application = relationship("ApplicationORM", back_populates="notes_list")


class IngestionRunORM(Base):
    __tablename__ = "ingestion_runs"

    id = Column(String, primary_key=True, default=generate_uuid)
    started_at = Column(DateTime, default=datetime.utcnow, index=True)
    completed_at = Column(DateTime, nullable=True)
    source = Column(String, nullable=False, index=True)
    jobs_fetched = Column(Integer, default=0)
    jobs_inserted = Column(Integer, default=0)
    jobs_updated = Column(Integer, default=0)
    duplicates_removed = Column(Integer, default=0)
    failures = Column(Integer, default=0)
    duration_ms = Column(Float, default=0.0)
    status = Column(String, default="Running")  # Running, Success, Failed, Partial

