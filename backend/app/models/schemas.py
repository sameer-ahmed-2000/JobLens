from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

# Shared / Common
class Skill(BaseModel):
    name: str
    years_experience: Optional[float] = None
    level: Optional[str] = None

# Resume Profiles
class Project(BaseModel):
    name: str
    description: str
    technologies: List[str]

class ResumeProfile(BaseModel):
    title: str
    years_experience: float
    skills: List[str]
    projects: List[Project]

# Job Postings
class RawPosting(BaseModel):
    id: str
    title: str
    company: str
    description: str
    url: Optional[str] = None
    source: Optional[str] = None
    last_seen_at: Optional[str] = None
    # Persisted pgvector embedding from embedding_worker — passed through the
    # pipeline so embed_node can skip recomputation for already-embedded postings.
    # Excluded from serialization so it never surfaces in API responses.
    embedding: Optional[List[float]] = Field(default=None, exclude=True)

class ScoredPosting(BaseModel):
    id: Optional[str] = None
    posting: RawPosting
    overall_score: float
    fit_rationale: str

# Gap Analysis
class JDRequirements(BaseModel):
    required_skills: List[str]
    nice_to_have_skills: Optional[List[str]] = None
    preferred_skills: Optional[List[str]] = None
    seniority_level: Optional[str] = None
    key_responsibilities: Optional[List[str]] = None
    years_experience: Optional[float] = None

class SkillGap(BaseModel):
    skill: str
    missing_skill: str = ""
    classification: str = "missing"
    importance: str = "required"
    suggestion: str = ""
    bridge_suggestion: str = ""

class GapReport(BaseModel):
    job_title: str
    company: str
    match_score: float
    confidence_score: Optional[float] = None
    confidence_reasoning: Optional[str] = None
    gaps: List[SkillGap]
    overall_recommendation: str
    overall_fit_summary: Optional[str] = None

class GapReportRequest(BaseModel):
    job_description: Optional[str] = None
    jd_text: Optional[str] = None
    posting_url: Optional[str] = None

class UserProfileSchema(BaseModel):
    id: str
    name: str
    email: str
    whatsapp_number: Optional[str] = None
    notify_threshold: float
    display_threshold: float
    quiet_hours_start: Optional[str] = None
    quiet_hours_end: Optional[str] = None
    timezone: Optional[str] = "Asia/Kolkata"

class UserProfileUpdateSchema(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    whatsapp_number: Optional[str] = None
    notify_threshold: Optional[float] = None
    display_threshold: Optional[float] = None
    quiet_hours_start: Optional[str] = None
    quiet_hours_end: Optional[str] = None
    timezone: Optional[str] = None

class NotificationItemSchema(BaseModel):
    id: str
    job_id: str
    title: str
    company: str
    score: float
    rationale: Optional[str] = None
    url: Optional[str] = None
    created_at: Any
    notified_at: Optional[Any] = None


class SignupRequest(BaseModel):
    name: str
    email: str
    invite_code: str
    whatsapp_number: Optional[str] = None
    title: Optional[str] = "Software Engineer"
    years_experience: Optional[float] = 0.0
    skills: Optional[List[str]] = []
    projects: Optional[List[Dict[str, Any]]] = []

class SignupResponse(BaseModel):
    user: UserProfileSchema
    raw_token: str

