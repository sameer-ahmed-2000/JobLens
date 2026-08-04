"""
title_matcher.py — title similarity scoring for hybrid job ranking.

Richer than fuzzy string matching: uses role-equivalency groups from
title_aliases.json so that "React Developer" ≈ "Frontend Engineer" scores near 1.0,
while "React Developer" vs "Machine Learning Engineer" scores near 0.1.

Public API:

    from app.services.title_matcher import title_similarity
    score = title_similarity(resume_title, job_title)  # float ∈ [0, 1]

Scoring logic (in priority order):
  1. Same equivalency group          → 0.95
  2. Identical normalised title slug → 1.0
  3. High Jaccard token overlap      → 0.5–0.85 (linear interpolation)
  4. No data (empty string)          → 0.5 (neutral; doesn't help or hurt)
  5. Clearly different domain        → ~0.05–0.2

Seniority alignment modifier (applied on top of base score):
  • Same seniority level             → +0.05 (small bonus, capped at 1.0)
  • Mismatch (e.g. Junior vs Senior) → −0.05 (small penalty)
  • Either side undetected           → ±0.0 (no adjustment)
"""
from __future__ import annotations

import json
import logging
import os
import re
from functools import lru_cache
from typing import Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Internal: seniority level keywords (mirrors title_aliases.json)
# ---------------------------------------------------------------------------
_SENIORITY_KEYWORDS: Dict[str, List[str]] = {
    "staff":  ["staff", "principal", "architect"],
    "lead":   ["lead", "tech lead", "technical lead"],
    "senior": ["senior", "sr"],
    "mid":    ["mid", "mid-level", "mid level", "intermediate"],
    "junior": ["junior", "entry level", "entry-level", "jr", "associate"],
}

_SENIORITY_ORDER = ["junior", "mid", "senior", "lead", "staff"]


def _detect_seniority(title_lower: str) -> Optional[str]:
    for level, keywords in _SENIORITY_KEYWORDS.items():
        for kw in keywords:
            if re.search(r"\b" + re.escape(kw) + r"\b", title_lower):
                return level
    return None


def _strip_seniority(title_lower: str) -> str:
    pattern = re.compile(
        r"\b(?:senior|sr\.?|junior|jr\.?|lead|staff|principal|architect|"
        r"mid[\s\-]?level|mid|intermediate|associate|entry[\s\-]?level)\b",
        re.IGNORECASE,
    )
    return pattern.sub("", title_lower).strip()


# ---------------------------------------------------------------------------
# Load title_aliases.json
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def _load_alias_groups() -> Tuple[Dict[str, str], ...]:
    """
    Returns a tuple of (canonical_slug, lowercased_variant) pairs, cached.

    Also returns the raw groups dict as the second element for equivalency checks.
    Cached with lru_cache so the file is read at most once per process.
    """
    try:
        base = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        path = os.path.join(base, "data", "title_aliases.json")
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("groups", {})
    except Exception as e:
        logger.warning(f"title_matcher: could not load title_aliases.json: {e}")
        return {}


def _canonical_slug(title: str, groups: dict) -> Optional[str]:
    """Return the canonical slug for a title, or None if not in any group."""
    title_lower = title.lower().strip()
    stripped = _strip_seniority(title_lower).strip()

    for slug, variants in groups.items():
        variants_lower = [v.lower() for v in variants]
        if title_lower in variants_lower or stripped in variants_lower:
            return slug

    return None


def _jaccard_token_similarity(a: str, b: str) -> float:
    """Token-level Jaccard similarity after stripping seniority and common stop words."""
    _STOP = frozenset({"engineer", "developer", "dev", "and", "the", "of", "for", "a"})

    def tokens(s: str) -> Set[str]:
        s = _strip_seniority(s.lower())
        return {t for t in re.split(r"\W+", s) if t and t not in _STOP and len(t) > 1}

    set_a, set_b = tokens(a), tokens(b)
    if not set_a and not set_b:
        return 0.5   # both empty → neutral
    if not set_a or not set_b:
        return 0.0
    intersection = set_a & set_b
    union = set_a | set_b
    return len(intersection) / len(union)


# ---------------------------------------------------------------------------
# Seniority modifier
# ---------------------------------------------------------------------------

def _seniority_modifier(resume_title: str, job_title: str) -> float:
    """Small ±0.05 modifier based on seniority alignment."""
    r_level = _detect_seniority(resume_title.lower())
    j_level = _detect_seniority(job_title.lower())

    if r_level is None or j_level is None:
        return 0.0   # can't compare → neutral
    if r_level == j_level:
        return 0.05  # same level bonus
    return -0.05     # any mismatch penalty (mild)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def title_similarity(
    resume_title: str,
    job_title: str,
) -> float:
    """
    Compute a title similarity score in [0, 1].

    Args:
        resume_title: The candidate's self-reported title (from resume).
        job_title:    The job posting's title.

    Returns:
        float in [0.0, 1.0]:
        - 1.0  identical normalised slugs
        - 0.95 same equivalency group (e.g. "React Developer" ≈ "Frontend Engineer")
        - 0.7–0.9 high Jaccard overlap
        - 0.5  neutral (missing / empty title data)
        - ~0.1 clearly different domains
    """
    if not resume_title or not job_title:
        return 0.5   # neutral — no penalty for missing data

    groups = _load_alias_groups()

    resume_slug = _canonical_slug(resume_title, groups)
    job_slug    = _canonical_slug(job_title, groups)

    # ---- 1. Identical canonical slug ----
    if resume_slug and job_slug and resume_slug == job_slug:
        base = 0.95
        modifier = _seniority_modifier(resume_title, job_title)
        return round(min(1.0, max(0.0, base + modifier)), 4)

    # ---- 2. Different canonical slugs → different domains ----
    if resume_slug and job_slug and resume_slug != job_slug:
        # Still compute Jaccard as a tiebreaker for partially overlapping titles
        jaccard = _jaccard_token_similarity(resume_title, job_title)
        base = 0.05 + 0.25 * jaccard   # max ~0.30 for cross-domain
        modifier = _seniority_modifier(resume_title, job_title)
        return round(min(1.0, max(0.0, base + modifier)), 4)

    # ---- 3. At least one title unrecognised → fall back to Jaccard ----
    jaccard = _jaccard_token_similarity(resume_title, job_title)
    # Map Jaccard [0, 1] → score [0.1, 0.90] to avoid extremes
    base = 0.1 + 0.80 * jaccard
    modifier = _seniority_modifier(resume_title, job_title)
    return round(min(1.0, max(0.0, base + modifier)), 4)
