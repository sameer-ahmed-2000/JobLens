import logging
from typing import Dict, Any, List
from app.models.schemas import SkillGap
from app.services.llm_router import llm_router
from app.nodes.compare_skills import load_resume_data

logger = logging.getLogger(__name__)

def bridge_generator_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """LangGraph node to generate interview bridge suggestions for partial skill matches via Ollama."""
    logger.info("Executing bridge_generator_node...")
    skill_gaps: List[SkillGap] = state.get("skill_gaps", [])
    
    if not skill_gaps:
        logger.warning("No skill gaps available for bridge generation.")
        return {"skill_gaps": []}

    resume = load_resume_data()
    resume_text = f"Title: {resume.get('title', '')}. Skills: {', '.join(resume.get('skills', []))}."
    projects_text = " ".join([f"Project {p.get('name', '')}: {p.get('description', '')} Technologies: {', '.join(p.get('technologies', []))}." for p in resume.get("projects", [])])

    partial_count = 0
    for gap in skill_gaps:
        if gap.classification == "have":
            gap.bridge_suggestion = "Direct match in resume experience."
            gap.suggestion = gap.bridge_suggestion
        elif gap.classification == "missing":
            gap.bridge_suggestion = "No evidence in resume; prioritize learning basics."
            gap.suggestion = gap.bridge_suggestion
        elif gap.classification == "partial":
            partial_count += 1
            prompt = f"""You are an AI interview coach.

Candidate Resume:
{resume_text}

Resume Projects:
{projects_text}

Target Skill:
{gap.skill}

Write ONE sentence explaining how the candidate can honestly relate existing experience to this skill.
Do NOT exaggerate.
Do NOT invent experience.
Maximum 30 words."""
            try:
                res = llm_router.generate(prompt=prompt)
                if not res or res.strip() == "Rationale unavailable.":
                    gap.bridge_suggestion = "Bridge suggestion unavailable."
                else:
                    gap.bridge_suggestion = res.strip()
            except Exception as e:
                logger.warning(f"Ollama bridge generation failed for skill '{gap.skill}': {e}")
                gap.bridge_suggestion = "Bridge suggestion unavailable."
                
            gap.suggestion = gap.bridge_suggestion

    logger.info(f"Bridge generation completed for {partial_count} partial skills.")
    return {"skill_gaps": skill_gaps}
