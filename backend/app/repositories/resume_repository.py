from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from app.models.orm import ResumeORM, ProjectORM, SkillORM, EmbeddingCacheORM

class ResumeRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_active_resume(self) -> Optional[Dict[str, Any]]:
        resume = self.session.query(ResumeORM).first()
        if not resume:
            return None
        return self._to_dict(resume)

    def get_by_user_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        resume = self.session.query(ResumeORM).filter(ResumeORM.user_id == user_id).first()
        if not resume:
            return None
        return self._to_dict(resume)

    def upsert_resume(
        self,
        user_id: str,
        title: str,
        years_experience: float,
        skills: List[str],
        projects: List[Dict[str, Any]],
        resume_id: Optional[str] = None
    ) -> Dict[str, Any]:
        resume = None
        if resume_id:
            resume = self.session.query(ResumeORM).filter(ResumeORM.id == resume_id).first()
        if not resume:
            resume = self.session.query(ResumeORM).filter(ResumeORM.user_id == user_id).first()

        if resume:
            resume.experience_years = years_experience
            resume.target_roles = [title] if title else []
            resume.version = (resume.version or 1) + 1
            # Clear existing projects and skills to replace with new ones
            self.session.query(ProjectORM).filter(ProjectORM.resume_id == resume.id).delete()
            self.session.query(SkillORM).filter(SkillORM.resume_id == resume.id).delete()
        else:
            resume = ResumeORM(
                user_id=user_id,
                experience_years=years_experience,
                target_roles=[title] if title else [],
                version=1
            )
            if resume_id:
                resume.id = resume_id
            self.session.add(resume)
            self.session.flush()

        for s_name in skills:
            s_orm = SkillORM(resume_id=resume.id, name=s_name)
            self.session.add(s_orm)

        for p_data in projects:
            p_orm = ProjectORM(
                resume_id=resume.id,
                name=p_data.get("name", "Project"),
                description=p_data.get("description", ""),
                tech_stack=p_data.get("technologies", p_data.get("tech_stack", [])),
                metrics=p_data.get("metrics", "")
            )
            self.session.add(p_orm)

        self.session.flush()
        return self._to_dict(resume)

    def get_embedding_cache(self, entity_type: str, entity_id: str, section: str = "primary") -> Optional[Any]:
        cache_item = self.session.query(EmbeddingCacheORM).filter(
            EmbeddingCacheORM.entity_type == entity_type,
            EmbeddingCacheORM.entity_id == entity_id,
            EmbeddingCacheORM.section == section
        ).first()
        return cache_item.embedding if cache_item else None

    def set_embedding_cache(self, entity_type: str, entity_id: str, section: str, embedding: Any) -> None:
        cache_item = self.session.query(EmbeddingCacheORM).filter(
            EmbeddingCacheORM.entity_type == entity_type,
            EmbeddingCacheORM.entity_id == entity_id,
            EmbeddingCacheORM.section == section
        ).first()
        if cache_item:
            cache_item.embedding = embedding
        else:
            cache_item = EmbeddingCacheORM(
                entity_type=entity_type,
                entity_id=entity_id,
                section=section,
                embedding=embedding
            )
            self.session.add(cache_item)
        self.session.flush()

    def _to_dict(self, resume: ResumeORM) -> Dict[str, Any]:
        title = resume.target_roles[0] if resume.target_roles else "AI Engineer"
        skills = [s.name for s in resume.skills]
        projects = []
        for p in resume.projects:
            projects.append({
                "name": p.name,
                "description": p.description,
                "technologies": p.tech_stack or [],
                "metrics": p.metrics
            })
        return {
            "id": resume.id,
            "user_id": resume.user_id,
            "title": title,
            "years_experience": resume.experience_years,
            "target_roles": resume.target_roles or [],
            "skills": skills,
            "projects": projects,
            "version": resume.version or 1
        }
