import time
import logging
from typing import TypedDict, List, Dict, Any, Optional
from langgraph.graph import StateGraph, START, END
from app.models.schemas import JDRequirements, SkillGap, GapReport
from app.nodes.extract_jd import extract_jd_node
from app.nodes.normalize_skills import normalize_skills_node
from app.nodes.compare_skills import compare_skills_node
from app.nodes.bridge_generator import bridge_generator_node
from app.nodes.generate_report import generate_report_node

logger = logging.getLogger("gap_graph")

class GapState(TypedDict, total=False):
    jd_text: str
    job_title: str
    company: str
    extracted_jd: Optional[JDRequirements]
    normalized_skills: List[str]
    skill_gaps: List[SkillGap]
    confidence_score: float
    confidence_reasoning: str
    overall_fit_summary: str
    gap_report: Optional[GapReport]

def timed_node(func, label: str):
    """Wrap a LangGraph node to log exact execution time."""
    def wrapper(state: GapState) -> Dict[str, Any]:
        t0 = time.perf_counter()
        result = func(state)
        elapsed = (time.perf_counter() - t0) * 1000
        if elapsed >= 1000:
            logger.info(f"{label} - {elapsed/1000:.2f} s")
        else:
            logger.info(f"{label} - {elapsed:.0f} ms")
        return result
    return wrapper

def build_gap_graph():
    """Build and compile the Gap Analyzer LangGraph workflow."""
    builder = StateGraph(GapState)
    
    builder.add_node("extract_jd", timed_node(extract_jd_node, "JD Extraction"))
    builder.add_node("normalize_skills", timed_node(normalize_skills_node, "Normalization"))
    builder.add_node("compare_skills", timed_node(compare_skills_node, "Comparison"))
    builder.add_node("bridge_generator", timed_node(bridge_generator_node, "Bridge Generation"))
    builder.add_node("generate_report", timed_node(generate_report_node, "Summary Generation"))
    
    builder.add_edge(START, "extract_jd")
    builder.add_edge("extract_jd", "normalize_skills")
    builder.add_edge("normalize_skills", "compare_skills")
    builder.add_edge("compare_skills", "bridge_generator")
    builder.add_edge("bridge_generator", "generate_report")
    builder.add_edge("generate_report", END)
    
    return builder.compile()

# Compile the graph
gap_graph = build_gap_graph()
