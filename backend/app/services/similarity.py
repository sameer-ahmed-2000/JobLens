import logging
from typing import List, Any
import numpy as np
from app.models.schemas import RawPosting, ScoredPosting

logger = logging.getLogger(__name__)

def cosine_similarity(vec1: Any, vec2: Any) -> float:
    """Compute cosine similarity between two vectors."""
    v1 = np.array(vec1, dtype=np.float32)
    v2 = np.array(vec2, dtype=np.float32)
    
    norm1 = np.linalg.norm(v1)
    norm2 = np.linalg.norm(v2)
    
    if norm1 == 0 or norm2 == 0:
        return 0.0
        
    sim = np.dot(v1, v2) / (norm1 * norm2)
    return float(np.clip(sim, -1.0, 1.0))

def rank_postings(
    postings: List[RawPosting], 
    posting_embeddings: List[Any], 
    resume_embedding: Any
) -> List[ScoredPosting]:
    """Rank postings against resume embedding with deterministic ordering."""
    if len(postings) != len(posting_embeddings):
        logger.error(f"Length mismatch: {len(postings)} postings vs {len(posting_embeddings)} embeddings")
        raise ValueError("Number of postings must match number of embeddings.")

    scored = []
    for posting, emb in zip(postings, posting_embeddings):
        sim = cosine_similarity(emb, resume_embedding)
        # Round slightly or keep float for overall_score
        score = round(sim, 4)
        scored_posting = ScoredPosting(
            posting=posting,
            overall_score=score,
            fit_rationale="Pending analysis..."
        )
        scored.append(scored_posting)

    # Deterministic sorting:
    # 1. overall_score descending (-sp.overall_score)
    # 2. title ascending (sp.posting.title)
    # 3. id ascending (sp.posting.id)
    scored.sort(key=lambda sp: (-sp.overall_score, sp.posting.title, sp.posting.id))
    
    logger.info(f"Ranked {len(scored)} postings successfully.")
    return scored
