import logging
import json
from typing import Dict, Any, List
from app.models.schemas import SkillGap
from app.services.llm_router_factory import get_llm_router
from app.nodes.compare_skills import load_resume_data

logger = logging.getLogger(__name__)

def bridge_generator_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """LangGraph node to generate interview bridge suggestions for partial skill matches via Ollama."""
    logger.info("Executing bridge_generator_node...")
    skill_gaps: List[SkillGap] = state.get("skill_gaps", [])
    
    if not skill_gaps:
        logger.warning("No skill gaps available for bridge generation.")
        return {"skill_gaps": []}

    user_id = state.get("user_id", "default-user-id")
    resume = None
    try:
        from app.repositories.uow import UnitOfWork
        with UnitOfWork() as uow:
            resume = uow.resumes.get_active(user_id)
            if resume:
                logger.info(f"Loaded active resume from database for bridge generation (user: {user_id}).")
    except Exception as e:
        logger.warning(f"Could not load active resume from DB: {e}; falling back to local file.")

    if not resume:
        resume = load_resume_data()

    resume_text = f"Title: {resume.get('title', '')}. Skills: {', '.join(resume.get('skills', []))}."
    projects_text = " ".join([f"Project {p.get('name', '')}: {p.get('description', '')} Technologies: {', '.join(p.get('technologies', []))}." for p in resume.get("projects", [])])

    partial_gaps = [g for g in skill_gaps if g.classification == "partial"]

    for gap in skill_gaps:
        if gap.classification == "have":
            gap.bridge_suggestion = "Direct match in resume experience."
            gap.suggestion = gap.bridge_suggestion
        elif gap.classification == "missing":
            gap.bridge_suggestion = "No evidence in resume; prioritize learning basics."
            gap.suggestion = gap.bridge_suggestion

    if partial_gaps:
        partial_skills_list = [g.skill for g in partial_gaps]
        prompt = f"""You are an AI interview coach.

Candidate Resume:
{resume_text}

Resume Projects:
{projects_text}

Target Skills:
{json.dumps(partial_skills_list)}

For EACH target skill, write ONE sentence (maximum 30 words) explaining how the candidate can honestly relate existing experience to that skill.
Do NOT exaggerate. Do NOT invent experience.

Return ONLY valid JSON mapping each skill name exact string to its 1-sentence bridge suggestion:
{{
  "SkillName1": "One sentence bridge suggestion...",
  "SkillName2": "One sentence bridge suggestion..."
}}"""

        suggestions_map = None
        router = get_llm_router("gap_analysis")

        # First attempt
        try:
            suggestions_map = router.generate_json(prompt=prompt)
        except Exception as e:
            logger.warning(f"Batched bridge generation attempt 1 failed: {e}")

        # Retry once if output was invalid or not a dict
        if not isinstance(suggestions_map, dict):
            logger.info("Retrying batched bridge generation once...")
            retry_prompt = f"""Return ONLY valid JSON mapping skills to 1-sentence interview suggestions.
Target Skills: {json.dumps(partial_skills_list)}
Candidate Resume: {resume_text}
Projects: {projects_text}
"""
            try:
                suggestions_map = router.generate_json(prompt=retry_prompt)
            except Exception as e:
                logger.warning(f"Batched bridge generation attempt 2 failed: {e}")

        # Normalize keys in response dict for matching
        normalized_map = {}
        if isinstance(suggestions_map, dict):
            for k, v in suggestions_map.items():
                if isinstance(v, str) and v.strip():
                    normalized_map[str(k).strip().lower()] = v.strip()

        # Map back to partial skill gaps
        for gap in partial_gaps:
            mapped_text = normalized_map.get(gap.skill.strip().lower())
            if mapped_text and mapped_text != "Rationale unavailable.":
                gap.bridge_suggestion = mapped_text
            else:
                gap.bridge_suggestion = "Bridge suggestion unavailable."
            gap.suggestion = gap.bridge_suggestion

    logger.info(f"Bridge generation completed for {len(partial_gaps)} partial skills in single batched LLM request.")
    return {"skill_gaps": skill_gaps}
