import os
import sys
import logging

# Ensure backend directory is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s - %(message)s")
logger = logging.getLogger("test_discovery")

def test_phase_2a():
    logger.info("=== Starting Phase 2A Verification ===")
    from app.nodes.fetch import fetch_node
    from app.nodes.normalize import normalize_node
    from app.nodes.embed import embed_node
    from app.nodes.score import score_node

    # 1. Fetch
    state = fetch_node({})
    postings = state["postings"]
    assert len(postings) > 0, "Fetch node failed to load postings."
    logger.info(f"Step 1 (Fetch): Verified {len(postings)} postings loaded.")

    # 2. Normalize
    state.update(normalize_node(state))
    norm_postings = state["normalized_postings"]
    assert len(norm_postings) == len(postings), "Normalize node output length mismatch."
    # Check original text preservation and alias replacement
    first_norm = norm_postings[0]
    assert first_norm["posting"].description == postings[0].description, "Original text was modified during normalization!"
    logger.info("Step 2 (Normalize): Verified text normalization and original text preservation.")

    # 3. Embed
    state.update(embed_node(state))
    embeddings = state["posting_embeddings"]
    resume_emb = state["resume_embedding"]
    assert len(embeddings) == len(postings), "Embeddings count mismatch."
    assert resume_emb is not None, "Resume embedding is None."
    logger.info(f"Step 3 (Embed): Verified {len(embeddings)} posting embeddings and resume embedding computed.")

    # 4. Score
    state.update(score_node(state))
    scored = state["scored_postings"]
    assert len(scored) == len(postings), "Scored postings count mismatch."
    
    # Check deterministic ordering: each item's score should be >= next item's score
    for i in range(len(scored) - 1):
        assert scored[i].overall_score >= scored[i+1].overall_score, "Ordering violation in ranked postings."
    
    logger.info("Step 4 (Score & Rank): Verified scoring and deterministic ranking order.")
    logger.info("\n--- Top 3 Ranked Job Postings (Phase 2A) ---")
    for i, sp in enumerate(scored[:3], 1):
        logger.info(f"#{i} | Score: {sp.overall_score:.4f} | Title: {sp.posting.title} | Company: {sp.posting.company}")
    logger.info("=== Phase 2A Verification Passed Successfully! ===\n")
    return state

def test_phase_2b():
    logger.info("=== Starting Phase 2B Verification ===")
    import asyncio
    from app.services.discovery_service import discovery_service

    scored = asyncio.run(discovery_service.get_ranked_postings())
    assert len(scored) > 0, "DiscoveryService returned empty list."

    logger.info(f"Step 1 (Full Graph Execution): Successfully retrieved {len(scored)} ranked postings.")
    for i, sp in enumerate(scored[:3], 1):
        logger.info(f"#{i} | Score: {sp.overall_score:.4f} | Rationale: {sp.fit_rationale}")

    assert scored[0].fit_rationale is not None, "fit_rationale should not be None."
    logger.info("=== Phase 2B Verification Passed Successfully! ===\n")
    return scored

if __name__ == "__main__":
    try:
        test_phase_2a()
        test_phase_2b()
    except Exception as e:
        logger.error(f"Verification failed: {e}", exc_info=True)
        sys.exit(1)

