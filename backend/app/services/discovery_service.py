import time
import logging
from typing import List
from fastapi import HTTPException
from app.models.schemas import ScoredPosting
from app.graphs.discovery_graph import discovery_graph
from app.config import settings

logger = logging.getLogger("discovery_service")

class DiscoveryService:
    async def get_ranked_postings(self) -> List[ScoredPosting]:
        """Execute the LangGraph Discovery workflow and return ranked job postings."""
        logger.info("Discovery started")
        t0 = time.perf_counter()
        try:
            state = discovery_graph.invoke({})
        except FileNotFoundError as e:
            logger.error(f"Discovery pipeline failed (File not found): {e}")
            raise HTTPException(status_code=404, detail=f"Data file missing: {str(e)}")
        except ValueError as e:
            logger.error(f"Discovery pipeline failed (Validation/JSON error): {e}")
            raise HTTPException(status_code=400, detail=f"Data error: {str(e)}")
        except Exception as e:
            logger.error(f"Discovery pipeline failed unexpectedly: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Internal error during discovery pipeline execution.")
        
        elapsed = time.perf_counter() - t0
        postings = state.get("postings", [])
        scored = state.get("scored_postings", [])
        top_n = min(settings.top_n_rationales, len(scored))
        
        logger.info(f"Loaded {len(postings)} postings")
        logger.info(f"Normalized {len(state.get('normalized_postings', []))} postings")
        logger.info(f"Embedded {len(state.get('posting_embeddings', []))} postings")
        logger.info("Resume embedded")
        logger.info("Similarity complete")
        logger.info(f"Top {top_n} selected")
        logger.info(f"Generated {top_n} rationales")
        logger.info("Discovery completed")
        logger.info(f"Total: {elapsed:.2f} s")
        
        return scored

# Singleton instance
discovery_service = DiscoveryService()
