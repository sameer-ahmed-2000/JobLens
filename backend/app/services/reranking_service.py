import time
import logging
import json
from typing import List, Dict, Any
from app.models.schemas import ScoredPosting, RerankResult
from app.services.llm_router_factory import get_llm_router

logger = logging.getLogger(__name__)

class RerankingService:
    def rerank_postings(self, resume_text: str, postings: List[ScoredPosting], top_n: int = 10) -> RerankResult:
        if not postings:
            return RerankResult(postings=[], model="none", provider="none", latency_ms=0, fallback_used=True)
            
        target_postings = postings[:top_n]
        remaining = postings[top_n:]
        
        router = get_llm_router("reranking")
        
        # Build prompt
        jobs_json = []
        for p in target_postings:
            jobs_json.append({
                "job_id": str(p.posting.id),
                "title": p.posting.title,
                "description": p.posting.description[:800] # Cap length to save context
            })
            
        prompt = f"""You are an expert technical recruiter matching a candidate to open jobs.
Here is the candidate's resume summary:
---
{resume_text}
---

Here are the top {len(target_postings)} jobs already selected by our hybrid scoring system:
---
{json.dumps(jobs_json)}
---

Your task:
Rank these jobs from best fit to worst fit for this specific candidate.
Do not introduce new jobs. Only use the job_ids provided.
Provide a short, one-line explanation for why each job was placed in its rank.

Return ONLY valid JSON matching this exact schema:
{{
  "ranking": [
    {{
      "job_id": "string",
      "reason": "string"
    }}
  ]
}}
"""
        
        t0 = time.perf_counter()
        raw_res = None
        try:
            raw_res = router.generate_json(prompt=prompt, timeout=45.0)
        except Exception as e:
            logger.error(f"Reranking LLM call failed: {e}")
            
        latency_ms = int((time.perf_counter() - t0) * 1000)
        provider = router.active_provider
        
        model = "unknown"
        if hasattr(router._backend, "model"):
            model = router._backend.model
        elif hasattr(router._backend, "model_name"):
            model = router._backend.model_name
        
        # Try to parse the result
        fallback_used = True
        if raw_res and isinstance(raw_res, dict) and "ranking" in raw_res:
            ranking_list = raw_res["ranking"]
            
            returned_ids = [str(r.get("job_id")) for r in ranking_list if r.get("job_id")]
            original_ids = [str(p.posting.id) for p in target_postings]
            
            # Check if LLM gave us enough of the jobs back
            if len(set(returned_ids).intersection(original_ids)) > 0:
                fallback_used = False
                
                reason_map = {str(r.get("job_id")): r.get("reason", "") for r in ranking_list if r.get("job_id")}
                
                def get_rank(job_id):
                    job_id_str = str(job_id)
                    try:
                        return returned_ids.index(job_id_str)
                    except ValueError:
                        return 999
                        
                target_postings.sort(key=lambda p: get_rank(p.posting.id))
                
                for p in target_postings:
                    p.reranked = True
                    p.rerank_provider = provider
                    p.rerank_latency_ms = latency_ms
                    p.rerank_fallback_used = False
                    if str(p.posting.id) in reason_map:
                        p.rerank_explanation = reason_map[str(p.posting.id)]
        
        if fallback_used:
            logger.warning("Reranking failed or returned invalid JSON. Falling back to hybrid ordering.")
            for p in target_postings:
                p.reranked = True
                p.rerank_provider = provider
                p.rerank_latency_ms = latency_ms
                p.rerank_fallback_used = True
                
        final_postings = target_postings + remaining
        
        return RerankResult(
            postings=final_postings,
            model=model,
            provider=provider,
            latency_ms=latency_ms,
            fallback_used=fallback_used
        )

reranking_service = RerankingService()
