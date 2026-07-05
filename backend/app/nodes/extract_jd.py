import logging
import json
import re
from typing import Dict, Any, List, Optional
from app.models.schemas import JDRequirements
from app.services.llm_router import llm_router
from app.nodes.normalize import get_tech_aliases

logger = logging.getLogger(__name__)

def extract_fallback_skills(text: str) -> List[str]:
    """Fallback skill extraction using known tech aliases if LLM fails or is unavailable."""
    if not text:
        return []
    aliases = get_tech_aliases()
    found_skills = set()
    text_lower = text.lower()
    
    # Check canonical values and alias keys
    for alias, canonical in aliases.items():
        if re.search(r"\b" + re.escape(alias.lower()) + r"\b", text_lower):
            found_skills.add(canonical)
        if re.search(r"\b" + re.escape(canonical.lower()) + r"\b", text_lower):
            found_skills.add(canonical)
            
    # Add common tech terms if present
    common = ["python", "java", "c++", "aws", "docker", "kubernetes", "sql", "git", "linux", "react", "fastapi", "langgraph", "llm", "rag", "machine learning"]
    for term in common:
        if re.search(r"\b" + re.escape(term) + r"\b", text_lower):
            # Format nicely
            found_skills.add(term.upper() if len(term) <= 3 else term.title() if term not in ("fastapi", "langgraph", "llm", "rag", "aws") else term.upper() if term in ("llm", "rag", "aws", "sql") else "FastAPI" if term == "fastapi" else "LangGraph")
            
    return sorted(list(found_skills))

def extract_jd_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """LangGraph node to extract structured job requirements from JD text via Ollama."""
    logger.info("Executing extract_jd_node...")
    jd_text = state.get("jd_text", "").strip()
    
    if not jd_text or len(jd_text) < 5:
        logger.error("JD Extraction failed: Invalid or empty job description text.")
        raise ValueError("Invalid or empty job description text provided.")

    prompt = f"""You are an expert HR and AI technical recruiter.
Analyze the following Job Description and extract the key requirements.
Return ONLY valid JSON matching this exact schema:
{{
  "required_skills": ["skill1", "skill2"],
  "nice_to_have_skills": ["skill3"],
  "seniority_level": "e.g. Senior, Mid-Level, Junior",
  "key_responsibilities": ["resp1", "resp2"]
}}

Job Description:
{jd_text[:3000]}
"""

    extracted_jd: Optional[JDRequirements] = None

    # First attempt
    try:
        raw_res = llm_router.generate_structured_output(prompt=prompt, schema=JDRequirements)
        if raw_res and isinstance(raw_res, dict):
            extracted_jd = JDRequirements(**raw_res)
        elif isinstance(raw_res, JDRequirements):
            extracted_jd = raw_res
    except Exception as e:
        logger.warning(f"JD extraction attempt 1 failed: {e}")

    # Retry once if parsing failed
    if not extracted_jd:
        logger.info("Retrying JD extraction once after initial failure...")
        retry_prompt = f"""Extract requirements from the job text below. You MUST return ONLY valid JSON with keys: "required_skills", "nice_to_have_skills", "seniority_level", "key_responsibilities".

Job Text:
{jd_text[:3000]}
"""
        try:
            raw_res_retry = llm_router.generate_structured_output(prompt=retry_prompt, schema=JDRequirements)
            if raw_res_retry and isinstance(raw_res_retry, dict):
                extracted_jd = JDRequirements(**raw_res_retry)
            elif isinstance(raw_res_retry, JDRequirements):
                extracted_jd = raw_res_retry
        except Exception as e:
            logger.warning(f"JD extraction attempt 2 (retry) failed: {e}")

    # Graceful degradation if LLM is unavailable, times out, or fails both attempts
    if not extracted_jd:
        logger.warning("LLM extraction failed or unavailable. Using deterministic keyword fallback for requirements extraction.")
        fallback_skills = extract_fallback_skills(jd_text)
        extracted_jd = JDRequirements(
            required_skills=fallback_skills if fallback_skills else ["General Software Engineering"],
            nice_to_have_skills=[],
            seniority_level="Not specified",
            key_responsibilities=["Execute core engineering responsibilities per job description."]
        )

    logger.info(f"JD Extraction completed. Found {len(extracted_jd.required_skills)} required skills.")
    return {"extracted_jd": extracted_jd}
