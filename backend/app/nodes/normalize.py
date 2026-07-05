import os
import re
import json
import html
from html.parser import HTMLParser
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class MLStripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self.reset()
        self.strict = False
        self.convert_charrefs = True
        self.text = []

    def handle_data(self, d):
        self.text.append(d)

    def get_data(self):
        return "".join(self.text)

def strip_html(text: str) -> str:
    """Strip HTML tags using standard library HTMLParser."""
    if not text:
        return ""
    text = html.unescape(text)
    s = MLStripper()
    try:
        s.feed(text)
        return s.get_data()
    except Exception:
        # Fallback if parser fails
        return re.sub(r"<[^>]+>", " ", text)

def load_tech_aliases(aliases_path: Optional[str] = None) -> Dict[str, str]:
    if aliases_path is None:
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        aliases_path = os.path.join(base_dir, "data", "tech_aliases.json")

    if not os.path.exists(aliases_path):
        logger.warning(f"Tech aliases file not found at {aliases_path}")
        return {}

    with open(aliases_path, "r", encoding="utf-8") as f:
        return json.load(f)

# Cache aliases globally
_TECH_ALIASES: Dict[str, str] = {}
def get_tech_aliases() -> Dict[str, str]:
    global _TECH_ALIASES
    if not _TECH_ALIASES:
        _TECH_ALIASES = load_tech_aliases()
    return _TECH_ALIASES

def normalize_text(text: str) -> str:
    """Normalize text: HTML stripping, whitespace normalization, and tech alias replacement."""
    if not text:
        return ""
        
    # 1. Strip HTML
    clean = strip_html(text)
    
    # 2. Tech alias replacement (sorted by length descending to match longest phrases first)
    aliases = get_tech_aliases()
    sorted_keys = sorted(aliases.keys(), key=len, reverse=True)
    for alias in sorted_keys:
        target = aliases[alias]
        # Use word boundary matching
        pattern = r"\b" + re.escape(alias) + r"\b"
        clean = re.sub(pattern, target, clean, flags=re.IGNORECASE)

    # 3. Normalize whitespace
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean

def normalize_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """LangGraph node to normalize postings while preserving original text."""
    logger.info("Executing normalize_node...")
    postings = state.get("postings", [])
    
    normalized_postings = []
    for p in postings:
        norm_title = normalize_text(p.title)
        norm_company = normalize_text(p.company)
        norm_desc = normalize_text(p.description)
        
        # Combine normalized fields for embedding and similarity matching
        combined_text = f"Title: {norm_title}. Company: {norm_company}. Description: {norm_desc}"
        
        normalized_postings.append({
            "posting": p,  # Original unmodified RawPosting object
            "normalized_title": norm_title,
            "normalized_company": norm_company,
            "normalized_description": norm_desc,
            "normalized_text": combined_text
        })
        
    logger.info(f"Normalized {len(normalized_postings)} postings successfully.")
    return {"normalized_postings": normalized_postings}
