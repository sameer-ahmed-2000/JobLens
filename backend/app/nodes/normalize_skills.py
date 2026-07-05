import os
import re
import json
import logging
from typing import Dict, Any, List
from app.nodes.normalize import get_tech_aliases

logger = logging.getLogger(__name__)

def normalize_skill_name(skill: str, aliases: Dict[str, str]) -> str:
    """Normalize a skill string using tech aliases."""
    if not skill:
        return ""
    cleaned = skill.strip()
    
    # 1. Exact case-insensitive lookup
    alias_map = {k.lower(): v for k, v in aliases.items()}
    if cleaned.lower() in alias_map:
        return alias_map[cleaned.lower()]
        
    # 2. Substring word-boundary replacement for phrases (longest first)
    sorted_keys = sorted(aliases.keys(), key=len, reverse=True)
    for alias in sorted_keys:
        target = aliases[alias]
        pattern = r"\b" + re.escape(alias) + r"\b"
        cleaned = re.sub(pattern, target, cleaned, flags=re.IGNORECASE)
        
    # Clean extra whitespace
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned

def normalize_skills_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """LangGraph node to normalize extracted skills against tech_aliases.json."""
    logger.info("Executing normalize_skills_node...")
    extracted_jd = state.get("extracted_jd")
    
    if not extracted_jd or not extracted_jd.required_skills:
        logger.warning("No required skills found in state to normalize.")
        return {"normalized_skills": []}

    aliases = get_tech_aliases()
    normalized_skills: List[str] = []
    seen = set()

    for skill in extracted_jd.required_skills:
        norm_skill = normalize_skill_name(skill, aliases)
        if norm_skill and norm_skill.lower() not in seen:
            seen.add(norm_skill.lower())
            normalized_skills.append(norm_skill)

    # Update extracted_jd in place with normalized skills
    extracted_jd.required_skills = normalized_skills

    logger.info(f"Normalized {len(normalized_skills)} required skills successfully.")
    return {
        "normalized_skills": normalized_skills,
        "extracted_jd": extracted_jd
    }
