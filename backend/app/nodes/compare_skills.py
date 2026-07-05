import os
import json
import logging
from typing import Dict, Any, List, Set
from app.models.schemas import SkillGap
from app.nodes.normalize_skills import normalize_skill_name
from app.nodes.normalize import get_tech_aliases

logger = logging.getLogger(__name__)

# Define transferable technology clusters for deterministic partial matching
TRANSFERABLE_CLUSTERS = [
    {"python", "fastapi", "django", "flask", "node.js", "express", "backend", "api", "rest api"},
    {"react", "vue.js", "angular", "next.js", "typescript", "javascript", "frontend", "web development"},
    {"langgraph", "langchain", "llama index", "rag", "llm", "ai", "genai", "generative ai", "machine learning", "deep learning", "nlp", "pytorch", "tensorflow", "openai", "huggingface", "vector database", "faiss", "pinecone", "qdrant"},
    {"aws", "gcp", "azure", "cloud", "cloud computing"},
    {"docker", "kubernetes", "k8s", "containerization", "docker compose"},
    {"kafka", "rabbitmq", "event streaming", "distributed systems", "pub/sub", "streaming"},
    {"postgresql", "mysql", "mongodb", "sqlite", "redis", "dynamodb", "sql", "nosql", "database"}
]

def load_resume_data(file_path: str = None) -> Dict[str, Any]:
    if file_path is None:
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        file_path = os.path.join(base_dir, "data", "resume.json")
        
    if not os.path.exists(file_path):
        logger.error(f"Resume file not found at: {file_path}")
        raise FileNotFoundError(f"Resume file not found at: {file_path}")
        
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)

def compare_skills_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """LangGraph node to deterministically compare required skills against candidate resume."""
    logger.info("Executing compare_skills_node...")
    normalized_skills = state.get("normalized_skills", [])
    
    if not normalized_skills:
        # If normalized_skills not set, try extracted_jd
        extracted_jd = state.get("extracted_jd")
        if extracted_jd and extracted_jd.required_skills:
            normalized_skills = extracted_jd.required_skills
            
    if not normalized_skills:
        logger.warning("No skills available for comparison.")
        return {"skill_gaps": []}

    resume = load_resume_data()
    aliases = get_tech_aliases()

    # Build candidate knowledge base
    candidate_skills: Set[str] = set()
    for s in resume.get("skills", []):
        norm_s = normalize_skill_name(s, aliases).lower()
        candidate_skills.add(norm_s)
        candidate_skills.add(s.lower())

    project_techs: Set[str] = set()
    project_descriptions: List[str] = []
    for p in resume.get("projects", []):
        for t in p.get("technologies", []):
            norm_t = normalize_skill_name(t, aliases).lower()
            project_techs.add(norm_t)
            project_techs.add(t.lower())
        desc = p.get("description", "")
        if desc:
            project_descriptions.append(desc.lower())

    direct_match_set = candidate_skills | project_techs
    all_resume_text = (
        resume.get("title", "") + " " +
        " ".join(resume.get("skills", [])) + " " +
        " ".join(project_descriptions) + " " +
        " ".join(project_techs)
    ).lower()

    skill_gaps: List[SkillGap] = []

    for req_skill in normalized_skills:
        req_lower = req_skill.lower().strip()
        classification = "missing"

        # 1. Direct Match (have)
        if req_lower in direct_match_set:
            classification = "have"
        else:
            # Check if any candidate skill or project tech equals or is contained in req_skill
            for cand_s in direct_match_set:
                if len(cand_s) >= 3 and (cand_s == req_lower or f" {cand_s} " in f" {req_lower} " or cand_s in req_lower.split()):
                    classification = "have"
                    break
            if classification != "have":
                for cand_s in direct_match_set:
                    if len(req_lower) >= 3 and req_lower in cand_s:
                        classification = "have"
                        break

        # 2. Partial Match (partial)
        if classification != "have":
            # Check transferable clusters
            is_transferable = False
            for cluster in TRANSFERABLE_CLUSTERS:
                if any(c == req_lower or c in req_lower.split() for c in cluster):
                    if any(c in direct_match_set for c in cluster):
                        is_transferable = True
                        break
            if is_transferable:
                classification = "partial"
            else:
                # Check significant word overlap in project descriptions or resume title
                words = [w for w in req_lower.split() if len(w) >= 3 and w not in ("and", "the", "with", "using", "for", "from", "system", "systems", "development")]
                if words and any(w in all_resume_text for w in words):
                    classification = "partial"

        # Construct SkillGap object
        gap = SkillGap(
            skill=req_skill,
            missing_skill=req_skill,
            classification=classification,
            importance="required",
            suggestion="",
            bridge_suggestion=""
        )
        skill_gaps.append(gap)

    have_count = sum(1 for g in skill_gaps if g.classification == "have")
    partial_count = sum(1 for g in skill_gaps if g.classification == "partial")
    missing_count = sum(1 for g in skill_gaps if g.classification == "missing")
    logger.info(f"Comparison complete: {have_count} have, {partial_count} partial, {missing_count} missing.")

    return {"skill_gaps": skill_gaps}
