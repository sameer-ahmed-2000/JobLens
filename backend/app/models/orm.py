import uuid
from datetime import datetime
from sqlalchemy import Column, String, Float, Integer, Boolean, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.database import Base

def generate_uuid():
    return str(uuid.uuid4())

class UserORM(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    resumes = relationship("ResumeORM", back_populates="user", cascade="all, delete-orphan")
    applications = relationship("ApplicationORM", back_populates="user", cascade="all, delete-orphan")


class ResumeORM(Base):
    __tablename__ = "resumes"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    experience_years = Column(Float, default=0.0)
    target_roles = Column(JSON, default=list)
    version = Column(Integer, default=1)

    user = relationship("UserORM", back_populates="resumes")
    projects = relationship("ProjectORM", back_populates="resume", cascade="all, delete-orphan")
    skills = relationship("SkillORM", back_populates="resume", cascade="all, delete-orphan")


class EmbeddingCacheORM(Base):
    __tablename__ = "embedding_cache"

    id = Column(String, primary_key=True, default=generate_uuid)
    entity_type = Column(String, nullable=False, index=True)  # e.g. "resume", "job", "company"
    entity_id = Column(String, nullable=False, index=True)
    section = Column(String, nullable=False, default="primary")  # e.g. "skills", "projects", "experience"
    embedding = Column(JSON, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ProjectORM(Base):
    __tablename__ = "projects"

    id = Column(String, primary_key=True, default=generate_uuid)
    resume_id = Column(String, ForeignKey("resumes.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    tech_stack = Column(JSON, default=list)
    metrics = Column(Text, nullable=True)

    resume = relationship("ResumeORM", back_populates="projects")


class SkillORM(Base):
    __tablename__ = "skills"

    id = Column(String, primary_key=True, default=generate_uuid)
    resume_id = Column(String, ForeignKey("resumes.id"), nullable=False, index=True)
    name = Column(String, nullable=False, index=True)
    years_experience = Column(Float, nullable=True)
    level = Column(String, nullable=True)

    resume = relationship("ResumeORM", back_populates="skills")


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
    status = Column(String, default="Saved")  # Saved, Applied, Assessment, OA, Interview, Offer, Rejected
    notes = Column(Text, nullable=True)
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

    application = relationship("ApplicationORM", back_populates="notes_list")
