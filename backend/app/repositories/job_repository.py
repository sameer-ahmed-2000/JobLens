from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from app.models.orm import JobORM, CompanyORM
from app.models.schemas import RawPosting

class JobRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_all_postings(self) -> List[RawPosting]:
        jobs = self.session.query(JobORM).all()
        result = []
        for j in jobs:
            result.append(self._to_pydantic(j))
        return result

    def get_by_id(self, job_id: str) -> Optional[RawPosting]:
        job = self.session.query(JobORM).filter(JobORM.id == job_id).first()
        return self._to_pydantic(job) if job else None

    def get_by_url(self, url: str) -> Optional[RawPosting]:
        job = self.session.query(JobORM).filter(JobORM.url == url).first()
        return self._to_pydantic(job) if job else None

    def get_by_id_or_url(self, identifier: str) -> Optional[RawPosting]:
        if not identifier:
            return None
        job = self.session.query(JobORM).filter(
            (JobORM.id == identifier) | (JobORM.url == identifier)
        ).first()
        return self._to_pydantic(job) if job else None

    def _resolve_company_id(self, company_name: Optional[str]) -> Optional[str]:
        if not company_name or not company_name.strip():
            return None
        c_name = company_name.strip()
        comp = self.session.query(CompanyORM).filter(CompanyORM.name.ilike(c_name)).first()
        if not comp:
            comp = CompanyORM(name=c_name)
            self.session.add(comp)
            self.session.flush()
        return comp.id

    def upsert(
        self,
        title: str,
        company_name: str,
        description: str,
        url: str,
        source: str = "Unknown",
        job_id: Optional[str] = None,
        company_id: Optional[str] = None,
        location: Optional[str] = None,
        employment_type: Optional[str] = None,
        salary: Optional[str] = None,
        salary_currency: Optional[str] = None,
        remote: Optional[bool] = None,
        seniority: Optional[str] = None,
        experience_required: Optional[float] = None,
        posted_date: Optional[str] = None,
        embedding: Optional[Any] = None
    ) -> RawPosting:
        job = self.session.query(JobORM).filter(JobORM.url == url).first()
        if not job and job_id:
            job = self.session.query(JobORM).filter(JobORM.id == job_id).first()

        resolved_company_id = company_id or self._resolve_company_id(company_name)

        if job:
            job.title = title
            job.description = description
            if resolved_company_id:
                job.company_id = resolved_company_id
            if source:
                job.source = source
            if location:
                job.location = location
            if employment_type:
                job.employment_type = employment_type
            if salary:
                job.salary = salary
            if salary_currency:
                job.salary_currency = salary_currency
            if remote is not None:
                job.remote = remote
            if seniority:
                job.seniority = seniority
            if experience_required is not None:
                job.experience_required = experience_required
            if posted_date:
                job.posted_date = posted_date
            if embedding is not None:
                job.embedding = embedding
            self.session.flush()
            self.session.refresh(job)
            return self._to_pydantic(job)
        else:
            job = JobORM(
                title=title,
                description=description,
                url=url,
                source=source,
                company_id=resolved_company_id,
                location=location,
                employment_type=employment_type,
                salary=salary,
                salary_currency=salary_currency,
                remote=remote,
                seniority=seniority,
                experience_required=experience_required,
                posted_date=posted_date,
                embedding=embedding
            )
            if job_id:
                job.id = job_id
            self.session.add(job)
            self.session.flush()
            self.session.refresh(job)
            return self._to_pydantic(job)

    def _to_pydantic(self, job: JobORM, comp_name_override: Optional[str] = None) -> RawPosting:
        comp_name = comp_name_override
        if not comp_name:
            if job.company:
                comp_name = job.company.name
            else:
                comp_name = "Unknown Company"
        return RawPosting(
            id=job.id,
            title=job.title,
            company=comp_name,
            description=job.description,
            url=job.url,
            source=job.source
        )
