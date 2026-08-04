import os
import json
import logging
from typing import Dict, Any, List, Set
from app.models.schemas import SkillGap
from app.nodes.normalize_skills import normalize_skill_name
from app.nodes.normalize import get_tech_aliases
from app.services.skill_matcher import SkillMatcher

logger = logging.getLogger(__name__)


def load_resume_data(file_path: str = None) -> Dict[str, Any]:
    if file_path is None:
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        file_path = os.path.join(base_dir, "data", "resume.json")
        
    if not os.path.exists(file_path):
        logger.error(f"Resume file not found at: {file_path}")
        raise FileNotFoundError(f"Resume file not found at: {file_path}")
        
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)

def compare_skills_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    LangGraph node — deterministic comparison of required skills against the resume.

    Delegates numeric matching to SkillMatcher, then converts the result into
    the List[SkillGap] presentation format expected by gap analysis consumers.
    Output contract is unchanged.
    """
    logger.info("Executing compare_skills_node...")
    normalized_skills = state.get("normalized_skills", [])
    
    if not normalized_skills:
        extracted_jd = state.get("extracted_jd")
        if extracted_jd and extracted_jd.required_skills:
            normalized_skills = extracted_jd.required_skills
            
    if not normalized_skills:
        logger.warning("No skills available for comparison.")
        return {"skill_gaps": []}

    user_id = state.get("user_id", "default-user-id")
    resume = None
    try:
        from app.repositories.uow import UnitOfWork
        with UnitOfWork() as uow:
            resume = uow.resumes.get_active(user_id)
            if resume:
                logger.info(f"Loaded active resume from database for skill comparison (user: {user_id}).")
    except Exception as e:
        logger.warning(f"Could not load active resume from DB: {e}; falling back to local file.")

    if not resume:
        resume = load_resume_data()
    aliases = get_tech_aliases()

    # Build candidate knowledge base (normalised)
    candidate_skills: Set[str] = set()
    for s in resume.get("skills", []):
        norm_s = normalize_skill_name(s, aliases).lower()
        candidate_skills.add(norm_s)
        candidate_skills.add(s.lower())

    project_techs: Set[str] = set()
    project_descriptions: List[str] = []
    for p in resume.get("projects", []):
        for t in p.get("technologies", []):
            norm_t = normalize_skill_name(t, aliases).lower()
            project_techs.add(norm_t)
            project_techs.add(t.lower())
        desc = p.get("description", "")
        if desc:
            project_descriptions.append(desc.lower())

    resume_text = (
        resume.get("title", "") + " " +
        " ".join(resume.get("skills", [])) + " " +
        " ".join(project_descriptions) + " " +
        " ".join(project_techs)
    ).lower()

    # Delegate numeric matching to SkillMatcher
    matcher = SkillMatcher()
    match_result = matcher.match(
        required_skills=normalized_skills,
        resume_skills=candidate_skills,
        resume_project_techs=project_techs,
        resume_text=resume_text,
        aliases=aliases,
    )

    # Convert SkillMatchResult back into the List[SkillGap] presentation format
    # (gap analysis consumers depend on this contract — do not change the output shape)
    matched_set = set(s.lower() for s in match_result.matched_skills)
    partial_set = set(s.lower() for s in match_result.partial_skills)

    skill_gaps: List[SkillGap] = []
    for req_skill in normalized_skills:
        req_lower = req_skill.lower().strip()
        if req_lower in matched_set:
            classification = "have"
        elif req_lower in partial_set:
            classification = "partial"
        else:
            classification = "missing"

        gap = SkillGap(
            skill=req_skill,
            missing_skill=req_skill,
            classification=classification,
            importance="required",
            suggestion="",
            bridge_suggestion=""
        )
        skill_gaps.append(gap)

    logger.info(
        f"Comparison complete: {match_result.matched} have, "
        f"{match_result.partial} partial, {len(match_result.missing_required)} missing."
    )
    return {"skill_gaps": skill_gaps}
