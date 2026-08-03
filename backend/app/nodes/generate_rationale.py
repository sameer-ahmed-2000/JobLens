import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

def generate_rationale_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    LangGraph node -- writes a placeholder rationale for all scored postings.
    Real rationale generation is intentionally NOT done here: it happens lazily,
    on-demand, via GET /api/matches/{match_id} (see app/routes/matches.py), which
    already implements this correctly. Generating rationales synchronously here
    was the root cause of 20-40s blocking on initial discovery for new users.
    """
    logger.info("Executing generate_rationale_node (placeholder-only, no LLM calls)...")
    scored_postings = state.get("scored_postings", [])

    for sp in scored_postings:
        sp.fit_rationale = "Click to analyze match fit"

    return {"scored_postings": scored_postings}
