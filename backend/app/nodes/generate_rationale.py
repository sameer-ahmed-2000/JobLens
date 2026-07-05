import logging
from typing import Dict, Any
from app.services.llm_router import llm_router
from app.services.resume_index import resume_index
from app.config import settings

logger = logging.getLogger(__name__)

def generate_rationale_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """LangGraph node to generate fit rationales via Ollama for Top N ranked jobs."""
    logger.info("Executing generate_rationale_node...")
    scored_postings = state.get("scored_postings", [])
    
    if not scored_postings:
        logger.warning("No scored postings available for rationale generation.")
        return {"scored_postings": []}

    top_n = settings.top_n_rationales
    resume_data = resume_index.get_resume_data()
    resume_skills = ", ".join(resume_data.get("skills", []))

    logger.info(f"Generating rationales for top {top_n} postings...")
    for i, sp in enumerate(scored_postings):
        if i < top_n:
            prompt = f"""You are an AI career advisor.
Resume Skills: {resume_skills}
Job Title: {sp.posting.title} at {sp.posting.company}
Job Description: {sp.posting.description[:400]}

Write ONE sentence.
Maximum 25 words.
Mention only overlapping skills.
Do not invent experience."""
            
            rationale = llm_router.generate(prompt=prompt)
            sp.fit_rationale = rationale
        else:
            sp.fit_rationale = f"Ranked outside top {top_n} (rationale not generated)."

    logger.info(f"Rationale generation complete for {len(scored_postings)} postings.")
    return {"scored_postings": scored_postings}
