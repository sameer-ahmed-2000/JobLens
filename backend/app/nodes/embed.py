import logging
import numpy as np
from typing import Dict, Any, List
from app.services.embeddings import embedding_service
from app.services.resume_index import resume_index

logger = logging.getLogger(__name__)


def embed_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    LangGraph node to generate vector embeddings for postings and resume.

    Reuses persisted embeddings from JobORM.embedding (populated by
    embedding_worker at ingestion time) where available, and only batch-
    computes embeddings for postings that don't have one yet.

    This eliminates redundant recomputation on every cache-miss for
    postings that are already fully embedded in the database.

    normalize_node stores the original RawPosting as item["posting"], so
    the cached embedding is pulled directly from item["posting"].embedding
    without any positional-zip against a separate postings list.
    """
    logger.info("Executing embed_node...")
    normalized_postings = state.get("normalized_postings", [])

    if not normalized_postings:
        logger.warning("No normalized postings found in state to embed.")
        return {"posting_embeddings": [], "resume_embedding": None}

    # Split into cached vs needs-compute, preserving original list order.
    # result_embeddings is pre-sized so both paths fill in by index.
    result_embeddings: List[Any] = [None] * len(normalized_postings)
    to_compute_idx: List[int] = []
    to_compute_texts: List[str] = []

    for i, item in enumerate(normalized_postings):
        posting = item["posting"]  # original RawPosting from normalize_node
        cached = getattr(posting, "embedding", None)
        if cached is not None:
            # Normalise to float32 numpy array — same dtype as embed_jobs output
            # so rank_postings/cosine_similarity sees a consistent type regardless
            # of which path produced the embedding.
            result_embeddings[i] = np.array(cached, dtype=np.float32)
        else:
            to_compute_idx.append(i)
            to_compute_texts.append(item["normalized_text"])

    cache_hits = len(normalized_postings) - len(to_compute_idx)

    if to_compute_texts:
        logger.info(
            f"Batch embedding {len(to_compute_texts)} of {len(normalized_postings)} postings "
            f"({cache_hits} cache hit(s), {len(to_compute_texts)} to compute)."
        )
        computed = embedding_service.embed_jobs(to_compute_texts)
        for idx, emb in zip(to_compute_idx, computed):
            result_embeddings[idx] = emb
    else:
        logger.info(
            f"All {len(normalized_postings)} postings had cached embeddings — no recomputation needed."
        )

    logger.info("Retrieving resume primary embedding...")
    resume_embedding = resume_index.get_primary_embedding()

    return {
        "posting_embeddings": result_embeddings,
        "resume_embedding": resume_embedding,
    }
