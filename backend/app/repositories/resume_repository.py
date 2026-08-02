from typing import Optional, Dict, Any, List
import logging
import numpy as np
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.models.orm import ResumeORM, EmbeddingCacheORM
from app.services.embeddings import embedding_service

logger = logging.getLogger(__name__)

class ResumeRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_active_resume(self) -> Optional[Dict[str, Any]]:
        """Fallback method retrieving the first active resume in the system."""
        resume = self.session.query(ResumeORM).filter(ResumeORM.is_active == True).first()
        if not resume:
            return None
        return self._to_dict(resume)

    def get_active(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve the active resume for a specific user."""
        resume = self.session.query(ResumeORM).filter(
            ResumeORM.user_id == user_id,
            ResumeORM.is_active == True
        ).first()
        if not resume:
            return None
        return self._to_dict(resume)

    def get_by_user_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Alias for get_active(user_id) to maintain compatibility."""
        return self.get_active(user_id)

    def get_by_id(self, resume_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a specific resume version by its ID."""
        resume = self.session.query(ResumeORM).filter(ResumeORM.id == resume_id).first()
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
        resume_id: Optional[str] = None,
        resume_file_id: Optional[str] = None,
        version: Optional[int] = None,
        parser_version: Optional[str] = None,
        raw_text: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Upsert a resume, recalculate the vector embedding, and mark it active.
        Ensures other resumes of this user are deactivated.
        """
        # Deactivate any other active resumes for this user
        self.session.query(ResumeORM).filter(
            ResumeORM.user_id == user_id,
            ResumeORM.is_active == True
        ).update({ResumeORM.is_active: False})

        # Construct raw_text representation
        structured_text = f"Title: {title}\nExperience: {years_experience} years\nSkills: {', '.join(skills)}"
        for p in projects:
            p_name = p.get("name") or p.get("title") or "Project"
            p_desc = p.get("description") or ""
            techs = p.get("technologies") or p.get("tech_stack") or []
            structured_text += f"\nProject {p_name}: {p_desc}"
            if techs:
                structured_text += f" (Tech: {', '.join(techs)})"

        if raw_text:
            combined_text = structured_text + "\n--- RAW EXTRACTED TEXT ---\n" + raw_text
        else:
            combined_text = structured_text

        # Compute embedding using embedding_service (mimicking resume_index logic)
        skills_text = "Skills: " + ", ".join(skills)
        project_descs = []
        for p in projects:
            techs = p.get("technologies") or p.get("tech_stack") or []
            tech_str = ", ".join(techs)
            project_descs.append(f"Project {p.get('name', '')}: {p.get('description', '')} Technologies used: {tech_str}.")
        projects_text = " ".join(project_descs)
        experience_text = f"Target Role: {title}. Professional experience: {years_experience} years in AI software engineering, LLM applications, and RAG systems."

        try:
            skill_emb = embedding_service.embed_resume_section(skills_text)
            project_emb = embedding_service.embed_resume_section(projects_text)
            experience_emb = embedding_service.embed_resume_section(experience_text)
            combined = skill_emb + project_emb + experience_emb
            norm = np.linalg.norm(combined)
            embedding = (combined / norm if norm > 0 else combined).tolist()
        except Exception as e:
            logger.warning(f"Failed to generate vector embedding for resume: {e}. Defaulting to zero vector.")
            embedding = [0.0] * 384

        # Check if resume already exists (by resume_file_id first, then by resume_id, then by raw_text/user_id)
        resume = None
        if resume_file_id:
            resume = self.session.query(ResumeORM).filter(ResumeORM.resume_file_id == resume_file_id).first()
        if not resume and resume_id:
            resume = self.session.query(ResumeORM).filter(ResumeORM.id == resume_id).first()
        if not resume:
            resume = self.session.query(ResumeORM).filter(
                ResumeORM.user_id == user_id, 
                ResumeORM.raw_text == combined_text
            ).first()

        if resume:
            resume.raw_text = combined_text
            resume.parsed_skills = skills
            resume.embedding = embedding
            resume.is_active = True
            if parser_version:
                resume.parser_version = parser_version
            if resume_file_id:
                resume.resume_file_id = resume_file_id
            if version:
                resume.version = version
        else:
            # Determine version if not passed
            if not version:
                max_ver = self.session.query(func.max(ResumeORM.version)).filter(ResumeORM.user_id == user_id).scalar() or 0
                version = max_ver + 1

            resume = ResumeORM(
                user_id=user_id,
                raw_text=combined_text,
                parsed_skills=skills,
                embedding=embedding,
                is_active=True,
                version=version,
                parser_version=parser_version,
                resume_file_id=resume_file_id
            )
            if resume_id:
                resume.id = resume_id
            self.session.add(resume)

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
        """
        Serializes ResumeORM to a dictionary format matching
        the expectations of other files and schemas.
        """
        # Parse experience and projects back out of raw_text for old-code compatibility
        title = "AI Engineer"
        years_experience = 0.0
        projects = []

        # Only split and parse from the structured prefix part of raw_text
        structured_part = resume.raw_text
        if "\n--- RAW EXTRACTED TEXT ---\n" in resume.raw_text:
            structured_part = resume.raw_text.split("\n--- RAW EXTRACTED TEXT ---\n", 1)[0]

        lines = structured_part.split("\n")
        if lines:
            # Parse title
            if lines[0].startswith("Title: "):
                title = lines[0][7:].strip()
            # Parse experience
            if len(lines) > 1 and lines[1].startswith("Experience: "):
                try:
                    exp_str = lines[1][12:].replace(" years", "").strip()
                    years_experience = float(exp_str)
                except ValueError:
                    pass
            # Parse projects
            for line in lines[2:]:
                if line.startswith("Project "):
                    try:
                        proj_part = line[8:]
                        name_part, desc_part = proj_part.split(":", 1)
                        name = name_part.strip()
                        desc = desc_part.strip()
                        
                        # Extract technologies
                        techs = []
                        if "(Tech: " in desc:
                            desc, tech_str = desc.rsplit("(Tech: ", 1)
                            techs = [t.strip() for t in tech_str.rstrip(")").split(",")]
                        projects.append({
                            "name": name,
                            "title": name,
                            "description": desc.strip(),
                            "technologies": techs,
                            "tech_stack": techs
                        })
                    except Exception:
                        pass

        # Extract only the actual raw text from raw_text column for UI display
        display_raw_text = resume.raw_text
        if "\n--- RAW EXTRACTED TEXT ---\n" in resume.raw_text:
            display_raw_text = resume.raw_text.split("\n--- RAW EXTRACTED TEXT ---\n", 1)[1]

        return {
            "id": resume.id,
            "user_id": resume.user_id,
            "title": title,
            "years_experience": years_experience,
            "skills": resume.parsed_skills or [],
            "parsed_skills": resume.parsed_skills or [],
            "projects": projects,
            "embedding": resume.embedding,
            "raw_text": display_raw_text,
            "is_active": resume.is_active,
            "created_at": resume.created_at
        }
