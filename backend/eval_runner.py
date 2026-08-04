import os
import json
import math
import argparse
from typing import List, Dict, Any

from app.services.embeddings import get_embedding
from app.services.similarity import cosine_similarity, hybrid_score
from app.services.skill_matcher import SkillMatcher
from app.services.title_matcher import title_similarity
from app.models.schemas import ScoredPosting, RawPosting, ScoreBreakdown
from app.services.reranking_service import reranking_service
from app.config import settings

def calculate_ndcg(predicted_order: List[float], k: int = 10) -> float:
    """
    Calculate NDCG@K.
    predicted_order contains the true relevance labels of the items,
    ordered by the algorithm's predicted ranking.
    """
    predicted_order = predicted_order[:k]
    
    dcg = sum(( (2 ** rel - 1) / math.log2(i + 2) ) for i, rel in enumerate(predicted_order))
    
    ideal_order = sorted(predicted_order, reverse=True)
    idcg = sum(( (2 ** rel - 1) / math.log2(i + 2) ) for i, rel in enumerate(ideal_order))
    
    if idcg == 0:
        return 0.0
    return dcg / idcg

def run_static_benchmark(dataset_path: str):
    print(f"\n--- Running Static Benchmark from {dataset_path} ---")
    with open(dataset_path, "r") as f:
        dataset = json.load(f)
        
    skill_matcher = SkillMatcher()
    
    metrics = {
        "v1": {"ndcg": []},
        "v2": {"ndcg": []},
        "v3": {"ndcg": []}
    }
    
    for case in dataset:
        print(f"\nEvaluating Resume: {case['resume_title']}")
        resume_text = case["resume_text"]
        resume_emb = get_embedding(resume_text)
        
        resume_skills = set(s.lower() for s in case["resume_skills"])
        resume_years = case["resume_years"]
        
        v1_results = []
        v2_results = []
        
        for job in case["jobs"]:
            job_emb = get_embedding(job["description"])
            label = job["label"]
            
            # v1: Semantic only
            sem_sim = cosine_similarity(job_emb, resume_emb)
            v1_results.append({
                "job_id": job["job_id"],
                "score": sem_sim,
                "label": label,
                "raw_posting": job
            })
            
            # v2: Hybrid
            req_skills = job["required_skills"]
            match_res = skill_matcher.match(req_skills, resume_skills, set(), resume_text)
            title_sim = title_similarity(case["resume_title"], job["title"])
            exp_score = skill_matcher.experience_score(resume_years, job["required_years"])
            
            breakdown = hybrid_score(
                semantic_sim=sem_sim,
                skill_score=match_res.score,
                title_score=title_sim,
                experience_score=exp_score,
                missing_required_count=len(match_res.missing_required),
                weights=settings
            )
            
            v2_results.append({
                "job_id": job["job_id"],
                "score": breakdown.final,
                "label": label,
                "raw_posting": job
            })
            
        # Sort and calc NDCG for v1
        v1_results.sort(key=lambda x: x["score"], reverse=True)
        v1_ndcg = calculate_ndcg([x["label"] for x in v1_results], k=5)
        metrics["v1"]["ndcg"].append(v1_ndcg)
        
        # Sort and calc NDCG for v2
        v2_results.sort(key=lambda x: x["score"], reverse=True)
        v2_ndcg = calculate_ndcg([x["label"] for x in v2_results], k=5)
        metrics["v2"]["ndcg"].append(v2_ndcg)
        
        # v3: Reranking top N of v2
        # Build ScoredPosting objects for reranking
        scored_postings = []
        for v2_res in v2_results:
            rp = RawPosting(
                id=v2_res["job_id"],
                title=v2_res["raw_posting"]["title"],
                company="Unknown",
                description=v2_res["raw_posting"]["description"]
            )
            sp = ScoredPosting(
                posting=rp,
                overall_score=v2_res["score"],
                fit_rationale="N/A"
            )
            scored_postings.append((sp, v2_res["label"]))
            
        sp_list = [t[0] for t in scored_postings]
        label_map = {t[0].posting.id: t[1] for t in scored_postings}
        
        # Rerank all 5
        print("  Running LLM Reranking (v3)...")
        rerank_res = reranking_service.rerank_postings(resume_text, sp_list, top_n=5)
        
        v3_labels = [label_map[p.posting.id] for p in rerank_res.postings]
        v3_ndcg = calculate_ndcg(v3_labels, k=5)
        metrics["v3"]["ndcg"].append(v3_ndcg)
        
        print(f"  v1 NDCG@5: {v1_ndcg:.4f}")
        print(f"  v2 NDCG@5: {v2_ndcg:.4f}")
        print(f"  v3 NDCG@5: {v3_ndcg:.4f}")
        
    print("\n=== Final Benchmark Results ===")
    v1_avg = sum(metrics["v1"]["ndcg"]) / len(metrics["v1"]["ndcg"])
    v2_avg = sum(metrics["v2"]["ndcg"]) / len(metrics["v2"]["ndcg"])
    v3_avg = sum(metrics["v3"]["ndcg"]) / len(metrics["v3"]["ndcg"])
    
    print(f"Semantic (v1) NDCG@5: {v1_avg:.4f}")
    print(f"Hybrid (v2) NDCG@5:   {v2_avg:.4f}")
    print(f"Hybrid+LLM (v3) NDCG@5: {v3_avg:.4f}")

def run_distribution_analysis():
    print("\n--- Running Live DB Distribution Analysis ---")
    try:
        from app.repositories.uow import UnitOfWork
        with UnitOfWork() as uow:
            v1_scores = []
            v2_scores = []
            v3_scores = []
            
            # Simple query to get distributions
            cursor = uow.session.execute("SELECT scoring_version, score FROM job_matches")
            for row in cursor:
                ver, score = row
                if ver == "v1" or ver is None:
                    v1_scores.append(score)
                elif ver == "v2":
                    v2_scores.append(score)
                elif ver == "v3":
                    v3_scores.append(score)
                    
            def stat(arr):
                if not arr: return "N/A"
                return f"Avg: {sum(arr)/len(arr):.4f} | Min: {min(arr):.4f} | Max: {max(arr):.4f} | Count: {len(arr)}"
                
            print(f"v1 (Semantic): {stat(v1_scores)}")
            print(f"v2 (Hybrid):   {stat(v2_scores)}")
            print(f"v3 (Reranked): {stat(v3_scores)}")
            
    except Exception as e:
        print(f"Distribution analysis failed: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="JobLens Offline Evaluation Runner")
    parser.add_argument("--mode", choices=["static", "live", "both"], default="both", help="Evaluation mode to run")
    parser.add_argument("--dataset", default="data/benchmark_dataset.json", help="Path to static benchmark dataset")
    args = parser.parse_args()
    
    # We must explicitly enable reranking for eval script to test v3 if it's off by default
    settings.reranking_enabled = True
    
    if args.mode in ["static", "both"]:
        run_static_benchmark(args.dataset)
        
    if args.mode in ["live", "both"]:
        run_distribution_analysis()
