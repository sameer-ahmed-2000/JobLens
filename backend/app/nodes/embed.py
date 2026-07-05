import logging
from typing import Dict, Any, List
from app.services.embeddings import embedding_service
from app.services.resume_index import resume_index

logger = logging.getLogger(__name__)

def embed_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """LangGraph node to generate vector embeddings for postings and resume."""
    logger.info("Executing embed_node...")
    normalized_postings = state.get("normalized_postings", [])
    
    if not normalized_postings:
        logger.warning("No normalized postings found in state to embed.")
        return {"posting_embeddings": [], "resume_embedding": None}

    texts_to_embed = [item["normalized_text"] for item in normalized_postings]
    logger.info(f"Batch embedding {len(texts_to_embed)} postings using instruction prefix...")
    posting_embeddings = embedding_service.embed_jobs(texts_to_embed)
    
    logger.info("Retrieving resume primary embedding...")
    resume_embedding = resume_index.get_primary_embedding()
    
    # Convert numpy arrays to list if needed, but numpy array list is fine in state
    return {
        "posting_embeddings": list(posting_embeddings),
        "resume_embedding": resume_embedding
    }
