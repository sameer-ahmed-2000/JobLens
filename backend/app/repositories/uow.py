from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.repositories.user_repository import UserRepository
from app.repositories.company_repository import CompanyRepository
from app.repositories.job_repository import JobRepository
from app.repositories.resume_repository import ResumeRepository
from app.repositories.gap_repository import GapRepository
from app.repositories.application_repository import ApplicationRepository

class UnitOfWork:
    def __init__(self, session_factory=SessionLocal):
        self.session_factory = session_factory
        self.session: Session = None

    def __enter__(self):
        self.session = self.session_factory()
        self.users = UserRepository(self.session)
        self.companies = CompanyRepository(self.session)
        self.jobs = JobRepository(self.session)
        self.resumes = ResumeRepository(self.session)
        self.gaps = GapRepository(self.session)
        self.applications = ApplicationRepository(self.session)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.rollback()
        self.session.close()

    def commit(self):
        self.session.commit()

    def rollback(self):
        self.session.rollback()
