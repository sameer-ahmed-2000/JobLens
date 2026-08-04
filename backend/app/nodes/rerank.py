import logging
from typing import Dict, Any
from app.config import settings

logger = logging.getLogger(__name__)

def rerank_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    LangGraph node — conditionally reranks the top N jobs using LLM.
    Updates the scoring_version to 'v3' if reranking successfully occurred.
    """
    scored_postings = state.get("scored_postings", [])
    
    # Fast path: disabled, no postings, or invalid configuration
    if not settings.reranking_enabled or not scored_postings:
        return {"scored_postings": scored_postings}
        
    top_n = settings.reranking_top_n
    
    # We only want to spend tokens reranking if we have strong candidates.
    # We check if there's at least one candidate that meets the display threshold,
    # or just rerank the top N. The user recommended:
    # "Only rerank if Top N <= 10 AND Hybrid score >= display_threshold"
    if top_n > 10:
        logger.warning(f"Reranking top_n ({top_n}) is > 10. Skipping rerank to save tokens.")
        return {"scored_postings": scored_postings}
        
    user_id = state.get("user_id", "default-user-id")
    
    # Get user's display threshold
    display_threshold = 0.5 # Default
    try:
        from app.repositories.uow import UnitOfWork
        with UnitOfWork() as uow:
            user = uow.users.get_by_id(user_id)
            if user:
                display_threshold = user.display_threshold
    except Exception as e:
        logger.warning(f"Could not load user {user_id} for threshold check: {e}")
        
    # Are there any candidates worth reranking?
    valid_candidates = [p for p in scored_postings[:top_n] if p.overall_score >= display_threshold]
    if not valid_candidates:
        logger.info(f"No top candidates meet display threshold ({display_threshold}). Skipping LLM rerank.")
        return {"scored_postings": scored_postings}
        
    logger.info(f"Executing rerank_node for top {len(valid_candidates)} candidates...")
    
    # Load resume_text
    resume_text = ""
    try:
        from app.repositories.uow import UnitOfWork
        with UnitOfWork() as uow:
            active_resume = uow.resumes.get_active(user_id)
            if active_resume:
                resume_title = active_resume.get("title", "")
                raw = active_resume.get("raw_text", "") or ""
                resume_text = (
                    resume_title + " " +
                    " ".join(active_resume.get("skills", [])) + " " +
                    raw[:1500]
                ).lower()
    except Exception as e:
        logger.warning(f"Could not load active resume from DB in rerank_node: {e}")
        
    if not resume_text:
        # Fallback
        try:
            from app.services.resume_index import resume_index
            resume_data = resume_index.get_resume_data()
            resume_title = resume_data.get("title", "")
            raw = resume_data.get("raw_text", "") or ""
            resume_text = (
                resume_title + " " +
                " ".join(resume_data.get("skills", [])) + " " +
                raw[:1500]
            ).lower()
        except Exception:
            logger.warning("No fallback resume text found.")
            
    if not resume_text:
        return {"scored_postings": scored_postings}
        
    # Do the rerank!
    from app.services.reranking_service import reranking_service
    
    result = reranking_service.rerank_postings(
        resume_text=resume_text,
        postings=scored_postings,
        top_n=len(valid_candidates)
    )
    
    new_version = "v3" if not result.fallback_used else state.get("scoring_version", "v2")
    
    logger.info(f"Reranking complete. Fallback used: {result.fallback_used}. Version: {new_version}")
    
    return {
        "scored_postings": result.postings,
        "scoring_version": new_version
    }
