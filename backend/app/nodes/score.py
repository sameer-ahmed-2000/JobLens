import logging
from typing import Dict, Any
from app.services.similarity import rank_postings

logger = logging.getLogger(__name__)

def score_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    LangGraph node to score and rank postings against resume embedding.
    Pulls active resume embedding from ResumeRepository.get_active(user_id) in database,
    falling back to the local index file.
    """
    logger.info("Executing score_node...")
    postings = state.get("postings", [])
    posting_embeddings = state.get("posting_embeddings", [])
    user_id = state.get("user_id", "default-user-id")

    # Attempt to pull active resume embedding from database
    resume_embedding = None
    try:
        from app.repositories.uow import UnitOfWork
        with UnitOfWork() as uow:
            active_resume = uow.resumes.get_active(user_id)
            if active_resume and active_resume.get("embedding") is not None:
                resume_embedding = active_resume["embedding"]
                logger.info(f"Loaded active resume embedding from database for user {user_id}.")
    except Exception as e:
        logger.warning(f"Could not load active resume embedding from DB: {e}; falling back to local file.")

    # Fallback to local file-based resume index
    if resume_embedding is None:
        logger.info("Falling back to local file resume index for embedding...")
        from app.services.resume_index import resume_index
        resume_embedding = resume_index.get_primary_embedding()

    if not postings or not posting_embeddings or resume_embedding is None:
        logger.warning("Missing postings, embeddings, or resume embedding for scoring.")
        return {"scored_postings": []}

    scored_postings = rank_postings(postings, posting_embeddings, resume_embedding)
    logger.info(f"Successfully ranked {len(scored_postings)} postings.")
    return {"scored_postings": scored_postings}
