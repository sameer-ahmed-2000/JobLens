import logging
from typing import Any, List, Optional, TYPE_CHECKING
import numpy as np
from app.models.schemas import RawPosting, ScoredPosting

if TYPE_CHECKING:
    from app.models.schemas import ScoreBreakdown

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


def hybrid_score(
    semantic_sim: float,
    skill_score: float,
    title_score: float,
    experience_score: float,
    missing_required_count: int,
    weights,  # app.config.Settings or any object with weight attributes
) -> "ScoreBreakdown":
    """
    Compute the weighted hybrid score and return a full ScoreBreakdown.

    Formula:
        raw = w_semantic * semantic
            + w_skill    * skill
            + w_title    * title
            + w_exp      * experience
        penalty = missing_required_count * required_skill_penalty
        final   = max(0.0, raw - penalty)

    Args:
        semantic_sim:          Cosine similarity ∈ [-1, 1]
        skill_score:           SkillMatcher.match().score ∈ [0, 1]
        title_score:           title_matcher.title_similarity() ∈ [0, 1]
        experience_score:      SkillMatcher.experience_score() ∈ [0.1, 1]
        missing_required_count: Number of required skills classified "missing"
        weights:               Object with scoring_weight_* and required_skill_penalty attrs

    Returns:
        ScoreBreakdown with all sub-scores and the final weighted score.
    """
    from app.models.schemas import ScoreBreakdown

    raw = (
        weights.scoring_weight_semantic   * semantic_sim
        + weights.scoring_weight_skill    * skill_score
        + weights.scoring_weight_title    * title_score
        + weights.scoring_weight_experience * experience_score
    )
    penalty = missing_required_count * weights.required_skill_penalty
    final = max(0.0, round(raw - penalty, 4))

    return ScoreBreakdown(
        semantic=round(float(semantic_sim), 4),
        skill=round(float(skill_score), 4),
        title=round(float(title_score), 4),
        experience=round(float(experience_score), 4),
        penalty=round(float(penalty), 4),
        final=final,
    )


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

