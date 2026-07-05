import time
import logging
from typing import TypedDict, List, Dict, Any, Optional
from langgraph.graph import StateGraph, START, END
from app.models.schemas import RawPosting, ScoredPosting
from app.nodes.fetch import fetch_node
from app.nodes.normalize import normalize_node
from app.nodes.embed import embed_node
from app.nodes.score import score_node
from app.nodes.generate_rationale import generate_rationale_node

logger = logging.getLogger("discovery_graph")

class DiscoveryState(TypedDict):
    postings: List[RawPosting]
    normalized_postings: List[Dict[str, Any]]
    posting_embeddings: List[Any]
    resume_embedding: Any
    scored_postings: List[ScoredPosting]

def timed_node(func, label: str):
    """Wrap a LangGraph node to log exact execution time."""
    def wrapper(state: DiscoveryState) -> Dict[str, Any]:
        t0 = time.perf_counter()
        result = func(state)
        elapsed = (time.perf_counter() - t0) * 1000
        if elapsed >= 1000:
            logger.info(f"{label} - {elapsed/1000:.2f} s")
        else:
            logger.info(f"{label} - {elapsed:.0f} ms")
        return result
    return wrapper

def build_discovery_graph():
    """Build and compile the Discovery LangGraph workflow."""
    builder = StateGraph(DiscoveryState)
    
    builder.add_node("fetch", timed_node(fetch_node, "Fetch"))
    builder.add_node("normalize", timed_node(normalize_node, "Normalize"))
    builder.add_node("embed", timed_node(embed_node, "Embedding"))
    builder.add_node("score", timed_node(score_node, "Scoring & Ranking"))
    builder.add_node("generate_rationale", timed_node(generate_rationale_node, "LLM Rationale"))
    
    builder.add_edge(START, "fetch")
    builder.add_edge("fetch", "normalize")
    builder.add_edge("normalize", "embed")
    builder.add_edge("embed", "score")
    builder.add_edge("score", "generate_rationale")
    builder.add_edge("generate_rationale", END)
    
    return builder.compile()

# Compile the graph
discovery_graph = build_discovery_graph()
