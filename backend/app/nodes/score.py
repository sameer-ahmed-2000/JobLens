import logging
from typing import Dict, Any
from app.services.similarity import rank_postings

logger = logging.getLogger(__name__)

def score_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """LangGraph node to score and rank postings against resume embedding."""
    logger.info("Executing score_node...")
    postings = state.get("postings", [])
    posting_embeddings = state.get("posting_embeddings", [])
    resume_embedding = state.get("resume_embedding")

    if not postings or not posting_embeddings or resume_embedding is None:
        logger.warning("Missing postings, embeddings, or resume embedding for scoring.")
        return {"scored_postings": []}

    scored_postings = rank_postings(postings, posting_embeddings, resume_embedding)
    logger.info(f"Successfully ranked {len(scored_postings)} postings.")
    return {"scored_postings": scored_postings}
