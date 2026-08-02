import re
import logging
from typing import Dict, Any, List, Tuple
from app.models.schemas import ResumeProfile, Project
from app.services.llm_router_factory import get_llm_router
from app.nodes.extract_jd import extract_fallback_skills

logger = logging.getLogger(__name__)

def fallback_parse_resume(raw_text: str) -> ResumeProfile:
    """
    Deterministic heuristic parser to extract basic candidate info when LLM is unavailable.
    """
    logger.info("Running deterministic fallback parser for resume...")
    
    # 1. Estimate years of experience
    years = 0.0
    # Search for patterns like "3.5+ years", "4 years", "10 years of experience"
    matches = re.findall(r"(\d+(?:\.\d+)?)\+?\s*years?(?:\s+of)?\s+experience", raw_text.lower())
    if matches:
        try:
            years = max(float(m) for m in matches)
        except ValueError:
            pass
            
    # 2. Extract skills using the alias-based fallback extractor
    skills = extract_fallback_skills(raw_text)
    
    # 3. Estimate candidate's title
    title = "Software Engineer"
    common_titles = [
        "data scientist", "machine learning engineer", "ml engineer", "ai engineer",
        "frontend engineer", "backend engineer", "fullstack engineer", "full stack engineer",
        "software engineer", "devops engineer", "cloud engineer", "engineering manager",
        "mobile developer", "web developer", "systems engineer"
    ]
    # Check the first 15 non-empty lines for a match
    lines = [line.strip().lower() for line in raw_text.split("\n") if line.strip()][:15]
    found = False
    for line in lines:
        for t in common_titles:
            if t in line:
                title = t.title()
                found = True
                break
        if found:
            break
            
    # 4. Dummy projects placeholder
    projects = []
    # If we find project header sections, we can try to extract names, but keeping it empty or simple is safer
    
    return ResumeProfile(
        title=title,
        years_experience=years,
        skills=skills,
        projects=projects
    )

def parse_resume_text(raw_text: str) -> Tuple[ResumeProfile, str]:
    """
    Parses resume text into a structured ResumeProfile using LLM.
    Reuses the llm_router's fallback patterns.
    Returns: (ResumeProfile, parser_version)
    """
    prompt = f"""You are an expert HR and AI technical recruiter.
Analyze the following Resume Text and extract the candidate profile.
You MUST extract ALL projects, skills, and years of experience mentioned in the resume. Do not skip, merge, or omit any project.
Return ONLY valid JSON matching this exact schema:
{{
  "title": "e.g. Senior Machine Learning Engineer, Software Engineer",
  "years_experience": 4.5,
  "skills": ["Python", "PyTorch", "FastAPI", "React"],
  "projects": [
    {{
      "name": "Project Name",
      "description": "Project description",
      "technologies": ["Python", "FastAPI"]
    }}
  ]
}}

Resume Text:
{raw_text[:16000]}
"""

    extracted_profile = None
    parser_version = "v1-llm"

    # Attempt 1
    try:
        raw_res = get_llm_router("resume_parsing").generate_structured_output(prompt=prompt, schema=ResumeProfile)
        if raw_res and isinstance(raw_res, dict):
            extracted_profile = ResumeProfile(**raw_res)
        elif isinstance(raw_res, ResumeProfile):
            extracted_profile = raw_res
    except Exception as e:
        logger.warning(f"Resume parsing attempt 1 failed: {e}")

    # Attempt 2 (Retry with simplified prompt)
    if not extracted_profile:
        logger.info("Retrying resume parsing once after initial failure...")
        retry_prompt = f"""Extract profile details from the resume text below. You MUST return ONLY valid JSON with keys: "title", "years_experience", "skills", "projects" (each project must have "name", "description", "technologies").

Resume Text:
{raw_text[:16000]}
"""
        try:
            raw_res_retry = get_llm_router("resume_parsing").generate_structured_output(prompt=retry_prompt, schema=ResumeProfile)
            if raw_res_retry and isinstance(raw_res_retry, dict):
                extracted_profile = ResumeProfile(**raw_res_retry)
            elif isinstance(raw_res_retry, ResumeProfile):
                extracted_profile = raw_res_retry
        except Exception as e:
            logger.warning(f"Resume parsing attempt 2 (retry) failed: {e}")

    # Graceful degradation if LLM is unavailable, times out, or fails
    if not extracted_profile:
        logger.warning("LLM resume parsing failed or unavailable. Falling back to heuristic parser.")
        extracted_profile = fallback_parse_resume(raw_text)
        parser_version = "v1-fallback"

    logger.info(f"Resume parsing completed using {parser_version}. Extracted title: '{extracted_profile.title}', {len(extracted_profile.skills)} skills.")
    return extracted_profile, parser_version
