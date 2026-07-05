import os
import json
import logging
from typing import List, Dict, Any, Optional
import numpy as np
from app.services.interfaces import IResumeIndex
from app.services.embeddings import embedding_service
from app.repositories.uow import UnitOfWork

logger = logging.getLogger(__name__)

class ResumeIndex(IResumeIndex):
    def __init__(self, resume_path: Optional[str] = None):
        if resume_path is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            self.resume_path = os.path.join(base_dir, "data", "resume.json")
        else:
            self.resume_path = resume_path
            
        self.resume_data: Optional[Dict[str, Any]] = None
        self.skill_embedding: Optional[np.ndarray] = None
        self.project_embedding: Optional[np.ndarray] = None
        self.experience_embedding: Optional[np.ndarray] = None
        self.primary_embedding: Optional[np.ndarray] = None

    def load_and_embed(self, force_reload: bool = False) -> None:
        if self.primary_embedding is not None and not force_reload:
            return

        logger.info("Loading resume profile from PostgreSQL via ResumeRepository...")
        resume_id = "default-resume-id"
        try:
            with UnitOfWork() as uow:
                res_dict = uow.resumes.get_active_resume()
                if res_dict:
                    self.resume_data = res_dict
                    resume_id = str(res_dict.get("id", "default-resume-id"))
                    
                    # Check embedding cache
                    if not force_reload:
                        cached_emb = uow.resumes.get_embedding_cache("resume", resume_id, "primary")
                        if cached_emb is not None:
                            logger.info("Found cached primary embedding in EmbeddingCache.")
                            self.primary_embedding = np.array(cached_emb, dtype=np.float32)
                            return
        except Exception as e:
            logger.warning(f"Database lookup failed in ResumeIndex: {e}; falling back to filesystem.")

        if self.resume_data is None:
            if not os.path.exists(self.resume_path):
                logger.error(f"Resume file not found at {self.resume_path}")
                raise FileNotFoundError(f"Resume file not found at {self.resume_path}")

            logger.info(f"Loading resume from filesystem {self.resume_path}")
            with open(self.resume_path, "r", encoding="utf-8") as f:
                self.resume_data = json.load(f)

        # 1. Skills Text
        skills = self.resume_data.get("skills", [])
        skills_text = "Skills: " + ", ".join(skills)

        # 2. Projects Text
        projects = self.resume_data.get("projects", [])
        project_descs = []
        for p in projects:
            techs = ", ".join(p.get("technologies", []))
            project_descs.append(f"Project {p.get('name', '')}: {p.get('description', '')} Technologies used: {techs}.")
        projects_text = " ".join(project_descs)

        # 3. Experience / Target Role Text
        title = self.resume_data.get("title", "")
        years = self.resume_data.get("years_experience", 0)
        experience_text = f"Target Role: {title}. Professional experience: {years} years in AI software engineering, LLM applications, and RAG systems."

        logger.info("Computing separate embeddings for skills, projects, and experience...")
        self.skill_embedding = embedding_service.embed_resume_section(skills_text)
        self.project_embedding = embedding_service.embed_resume_section(projects_text)
        self.experience_embedding = embedding_service.embed_resume_section(experience_text)

        combined = self.skill_embedding + self.project_embedding + self.experience_embedding
        norm = np.linalg.norm(combined)
        self.primary_embedding = combined / norm if norm > 0 else combined
        logger.info("Resume embeddings computed successfully.")

        # Cache in DB
        try:
            with UnitOfWork() as uow:
                uow.resumes.set_embedding_cache("resume", resume_id, "primary", self.primary_embedding.tolist())
                uow.commit()
                logger.info("Saved resume primary embedding to EmbeddingCache.")
        except Exception as e:
            logger.warning(f"Could not save embedding to cache: {e}")

    def get_primary_embedding(self) -> np.ndarray:
        if self.primary_embedding is None:
            self.load_and_embed()
        return self.primary_embedding

    def get_resume_data(self) -> Dict[str, Any]:
        if self.resume_data is None:
            self.load_and_embed()
        return self.resume_data

    def add_resume(self, resume_id: str, skills: List[str], experience: str) -> bool:
        return True

    def search_skills(self, required_skills: List[str], top_k: int = 5) -> List[Dict[str, Any]]:
        return []

# Singleton instance
resume_index = ResumeIndex()
