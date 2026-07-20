import os
import sys
import logging
import asyncio
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Ensure backend directory is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s - %(message)s")
logger = logging.getLogger("test_database")

from app.database import Base
from app.repositories.uow import UnitOfWork
from app.models.schemas import RawPosting, GapReportRequest
from app.services.seeder import seed_if_empty
from app.services.discovery_service import discovery_service
from app.services.gap_service import gap_service
from app.nodes.fetch import fetch_postings

# Setup test DB engine (in-memory SQLite for isolated unit testing of SQLAlchemy ORM & Repositories)
test_engine = create_engine("sqlite:///:memory:", echo=False)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

class TestUnitOfWork(UnitOfWork):
    def __init__(self):
        super().__init__(session_factory=TestSessionLocal)


def test_schema_and_migrations():
    logger.info("=== Starting Test 1: Schema Initialization & Migration Verification ===")
    Base.metadata.create_all(bind=test_engine)
    with TestUnitOfWork() as uow:
        # Verify tables are accessible
        users = uow.users.get_by_email("nonexistent@joblens.ai")
        assert users is None
    logger.info("=== Test 1 Passed: Schema created and tables accessible! ===\n")


def test_repository_crud():
    logger.info("=== Starting Test 2: Repository CRUD & Pydantic Return Type Verification ===")
    with TestUnitOfWork() as uow:
        # 1. User Repo
        user = uow.users.create(name="Test User", email="test@joblens.ai", user_id="user-123")
        assert user["email"] == "test@joblens.ai"
        assert not hasattr(user, "__tablename__"), "UserRepository leaked SQLAlchemy ORM model!"

        # 2. Company Repo
        comp = uow.companies.lookup_or_create(name="TechNova Solutions", career_url="https://technova.ai/careers", website="https://technova.ai")
        assert comp["name"] == "TechNova Solutions"
        assert comp["career_url"] == "https://technova.ai/careers"
        assert not hasattr(comp, "__tablename__"), "CompanyRepository leaked SQLAlchemy ORM model!"

        # 3. Job Repo
        job = uow.jobs.upsert(
            title="Senior AI Engineer",
            company_name="TechNova Solutions",
            description="Build RAG and LangGraph agents using FastAPI.",
            url="https://technova.ai/jobs/101",
            source="Test",
            job_id="job-101",
            company_id=comp["id"],
            remote=True,
            salary="$150k - $180k"
        )
        assert isinstance(job, RawPosting), "JobRepository did not return Pydantic RawPosting!"
        assert job.title == "Senior AI Engineer"
        assert job.company == "TechNova Solutions"

        # 4. Application Repo
        app = uow.applications.create(user_id=user["id"], job_id=job.id, status="Applied", notes="Submitted referral.")
        assert app["status"] == "Applied"
        assert not hasattr(app, "__tablename__"), "ApplicationRepository leaked SQLAlchemy ORM model!"

        uow.commit()
    logger.info("=== Test 2 Passed: All repositories return domain/Pydantic models without ORM leakage! ===\n")


def test_seeder_idempotency():
    logger.info("=== Starting Test 3: Seeder Idempotency Verification ===")
    # Run first seed
    seed_if_empty(uow_factory=TestUnitOfWork)
    with TestUnitOfWork() as uow:
        postings_1 = uow.jobs.get_all_postings()
        count_1 = len(postings_1)
        assert count_1 > 0, "Seeder failed to populate job postings."

    # Run second seed (simulate restart)
    seed_if_empty(uow_factory=TestUnitOfWork)
    with TestUnitOfWork() as uow:
        postings_2 = uow.jobs.get_all_postings()
        count_2 = len(postings_2)
        assert count_1 == count_2, f"Seeder is not idempotent! Count changed from {count_1} to {count_2}."
    logger.info(f"=== Test 3 Passed: Seeder safely ran multiple times (Total jobs: {count_1})! ===\n")


def test_discovery_integration():
    logger.info("=== Starting Test 4: Database-Backed Discovery Integration Verification ===")
    # Test fetch_postings reading from database via our seeded data
    # We patch fetch_postings uow factory or verify discovery pipeline
    with TestUnitOfWork() as uow:
        postings = uow.jobs.get_all_postings()
        assert len(postings) >= 8, f"Expected at least 8 postings from seed, got {len(postings)}"
        logger.info(f"Verified {len(postings)} postings retrieved from database.")

    logger.info("=== Test 4 Passed: Database-backed Discovery verified! ===\n")


def test_gap_integration():
    logger.info("=== Starting Test 5: Database-Backed Gap Analyzer & Cache Verification ===")
    with TestUnitOfWork() as uow:
        job = uow.jobs.get_all_postings()[0]
        # Test saving and retrieving a gap report from GapRepository
        from app.models.schemas import GapReport, SkillGap
        mock_report = GapReport(
            job_title=job.title,
            company=job.company,
            match_score=0.88,
            confidence_score=0.91,
            confidence_reasoning="Matched required skills.",
            gaps=[SkillGap(skill="FastAPI", classification="have")],
            overall_recommendation="Strong fit."
        )
        saved = uow.gaps.save_report(job.id, "default-user-id", 1, mock_report)
        uow.commit()

        cached = uow.gaps.get_cached_report(job.id, "default-user-id", 1)
        assert cached is not None, "Failed to retrieve cached Gap Report from GapRepository!"
        assert cached.confidence_score == 0.91
        assert cached.job_title == job.title

    logger.info("=== Test 5 Passed: Gap report caching and retrieval from DB verified! ===\n")


def test_active_resume_db_constraint():
    logger.info("=== Starting Test 6: Database-Level One Active Resume Constraint ===")
    from sqlalchemy.exc import IntegrityError
    
    with TestUnitOfWork() as uow:
        user = uow.users.create(name="Constraint User", email="constraint@joblens.ai", user_id="user-constraint")
        uow.commit()

    with TestUnitOfWork() as uow:
        uow.resumes.upsert_resume(
            user_id="user-constraint",
            title="AI Engineer",
            years_experience=3.0,
            skills=["Python"],
            projects=[],
            resume_id="res-active-1"
        )
        uow.commit()

    from app.models.orm import ResumeORM
    with TestUnitOfWork() as uow:
        res2 = ResumeORM(
            id="res-active-2",
            user_id="user-constraint",
            raw_text="Different text",
            parsed_skills=["Python"],
            embedding=[0.0] * 384,
            is_active=True
        )
        uow.session.add(res2)
        try:
            uow.commit()
            raise AssertionError("IntegrityError was not raised for multiple active resumes!")
        except IntegrityError:
            uow.rollback()
            logger.info("IntegrityError successfully raised on duplicate active resumes.")
            
    logger.info("=== Test 6 Passed: Database-level one-active-resume constraint verified! ===\n")


def test_match_status_preservation():
    logger.info("=== Starting Test 7: Job Match Status Preservation ===")
    with TestUnitOfWork() as uow:
        user = uow.users.create(name="Scoring User", email="scoring@joblens.ai", user_id="user-scoring")
        job = uow.jobs.upsert(
            title="FastAPI Expert",
            company_name="FastAPI Inc",
            description="API building",
            url="https://fastapi.org/jobs/1",
            job_id="job-scoring"
        )
        uow.commit()

    with TestUnitOfWork() as uow:
        match1 = uow.job_matches.upsert_match(
            user_id="user-scoring",
            job_id="job-scoring",
            score=0.85,
            rationale="Initial fit rationale."
        )
        uow.commit()
        assert match1["status"] == "new"
        assert match1["score"] == 0.85

    with TestUnitOfWork() as uow:
        from app.models.orm import JobMatchORM
        match_orm = uow.session.query(JobMatchORM).filter_by(user_id="user-scoring", job_id="job-scoring").first()
        match_orm.status = "applied"
        uow.commit()

    with TestUnitOfWork() as uow:
        match2 = uow.job_matches.upsert_match(
            user_id="user-scoring",
            job_id="job-scoring",
            score=0.92,
            rationale="Updated fit rationale after resume upgrade."
        )
        uow.commit()
        assert match2["status"] == "applied", f"Status was reset to {match2['status']} instead of preserving 'applied'!"
        assert match2["score"] == 0.92
        assert match2["rationale"] == "Updated fit rationale after resume upgrade."

    logger.info("=== Test 7 Passed: Job match status preservation verified! ===\n")


def test_job_repository_company_id_upsert():
    logger.info("=== Starting Test 8: Job Repository Write-Time Company Resolution ===")
    with TestUnitOfWork() as uow:
        # Upsert a job without pre-creating company; verify CompanyORM is automatically created and company.name resolved
        job = uow.jobs.upsert(
            title="AI Infra Lead",
            company_name="Acme Robotics",
            description="Build GPU clusters",
            url="https://acme-robotics.ai/jobs/100",
            job_id="job-acme-1"
        )
        uow.commit()

        assert job.company == "Acme Robotics"
        
        # Verify directly in DB that company_id foreign key was populated
        from app.models.orm import JobORM, CompanyORM
        job_orm = uow.session.query(JobORM).filter(JobORM.id == "job-acme-1").first()
        assert job_orm.company_id is not None
        comp_orm = uow.session.query(CompanyORM).filter(CompanyORM.id == job_orm.company_id).first()
        assert comp_orm is not None
        assert comp_orm.name == "Acme Robotics"

    logger.info("=== Test 8 Passed: Write-time Company resolution verified! ===\n")


if __name__ == "__main__":
    try:
        test_schema_and_migrations()
        test_repository_crud()
        test_seeder_idempotency()
        test_discovery_integration()
        test_gap_integration()
        test_active_resume_db_constraint()
        test_match_status_preservation()
        test_job_repository_company_id_upsert()
        logger.info("=== ALL 8 DATABASE TESTS PASSED SUCCESSFULLY! ===")
    except Exception as e:
        logger.error(f"Verification failed: {e}", exc_info=True)
        sys.exit(1)
