import logging
from typing import Dict, Any, List
from app.models.schemas import SkillGap, GapReport
from app.services.llm_router import llm_router

logger = logging.getLogger(__name__)

def generate_report_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """LangGraph node to generate overall fit summary, confidence score, and compile the final GapReport."""
    logger.info("Executing generate_report_node...")
    skill_gaps: List[SkillGap] = state.get("skill_gaps", [])
    job_title = state.get("job_title", "Target Role")
    company = state.get("company", "Target Company")

    total_required = len(skill_gaps)
    have_names = [g.skill for g in skill_gaps if g.classification == "have"]
    partial_names = [g.skill for g in skill_gaps if g.classification == "partial"]
    missing_names = [g.skill for g in skill_gaps if g.classification == "missing"]

    have_count = len(have_names)
    partial_count = len(partial_names)
    missing_count = len(missing_names)

    # Calculate confidence_score
    if total_required > 0:
        matched_val = (have_count * 1.0) + (partial_count * 0.5)
        confidence_score = round(matched_val / total_required, 2)
    else:
        confidence_score = 1.0 if not missing_count else 0.0

    # Generate confidence_reasoning
    missing_str = f"Missing: {', '.join(missing_names[:3])}." if missing_names else "No major missing skills."
    have_str = f"Strong experience in {', '.join(have_names[:3])}." if have_names else ""
    confidence_reasoning = f"Matched {have_count} direct and {partial_count} partial skills out of {total_required} required skills. {have_str} {missing_str}".strip()

    # Generate overall_fit_summary using Ollama
    prompt = f"""You are an AI career advisor.
Summarize the candidate's fit for the position of {job_title} at {company}.
Matched Skills: {', '.join(have_names)}
Partial Skills: {', '.join(partial_names)}
Missing Skills: {', '.join(missing_names)}

Mention:
- Strengths
- Missing Skills
- Interview Preparation Priorities
Maximum 80 words.
Do not invent experience."""

    try:
        res = llm_router.generate(prompt=prompt)
        if not res or res.strip() == "Rationale unavailable.":
            overall_fit_summary = "Summary unavailable."
        else:
            overall_fit_summary = res.strip()
    except Exception as e:
        logger.warning(f"Ollama overall summary generation failed: {e}")
        overall_fit_summary = "Summary unavailable."

    # Compile final GapReport
    report = GapReport(
        job_title=job_title,
        company=company,
        match_score=confidence_score,
        confidence_score=confidence_score,
        confidence_reasoning=confidence_reasoning,
        gaps=skill_gaps,
        overall_recommendation=overall_fit_summary,
        overall_fit_summary=overall_fit_summary
    )

    logger.info(f"Summary Generation complete. Confidence Score: {confidence_score}")
    return {
        "gap_report": report,
        "confidence_score": confidence_score,
        "confidence_reasoning": confidence_reasoning,
        "overall_fit_summary": overall_fit_summary
    }
