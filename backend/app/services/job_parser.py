"""
job_parser.py — deterministic, LLM-free structured job field extractor.

Internal architecture (composable, each independently testable):

    JobParser
    ├── SkillExtractor      → required_skills, preferred_skills
    ├── ExperienceExtractor → required_years (float | None)
    ├── TitleNormalizer     → normalized_title (canonical slug)
    └── SeniorityDetector   → seniority ("Junior" | "Mid" | "Senior" | "Lead" | "Staff" | None)

Public API:

    from app.services.job_parser import extract_job_fields
    structured = extract_job_fields(title, description)

Parser version constant:

    JOB_PARSER_VERSION = "v1"

Stored on JobORM.job_parser_version so stale records can be identified and
reprocessed when parsing logic improves.
"""
from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Parser version — bump this string whenever extraction logic changes materially
# so stale JobORM rows can be identified and reprocessed.
# ---------------------------------------------------------------------------
JOB_PARSER_VERSION = "v1"

# ---------------------------------------------------------------------------
# Regex helpers
# ---------------------------------------------------------------------------

# Markers that split a JD into "required" vs "preferred/nice-to-have" sections
_PREFERRED_SECTION_PATTERN = re.compile(
    r"(?:nice[\s\-]to[\s\-]have|preferred|bonus|good[\s\-]to[\s\-]have|"
    r"desirable|plus|advantageous|optional|ideally|not required)",
    re.IGNORECASE,
)

# Common experience requirement patterns — ordered most-specific first
_EXPERIENCE_PATTERNS: List[re.Pattern] = [
    # "5+ years", "5-7 years", "at least 5 years", "minimum 5 years", "5 or more years"
    re.compile(r"(\d+)\s*\+\s*years?", re.IGNORECASE),
    re.compile(r"(\d+)[\s\-–]+\d+\s*years?", re.IGNORECASE),        # take the lower bound
    re.compile(r"(?:at\s+least|minimum|min\.?)\s*(\d+)\s*years?", re.IGNORECASE),
    re.compile(r"(\d+)\s*or\s*more\s*years?", re.IGNORECASE),
    re.compile(r"(\d+)\s*years?(?:\s+of)?\s+experience", re.IGNORECASE),
    re.compile(r"experience\s+of\s+(\d+)\s*years?", re.IGNORECASE),
    re.compile(r"(\d+)\s*years?", re.IGNORECASE),                    # bare "3 years" fallback
]

# Seniority keywords mapped to canonical level names
_SENIORITY_MAP: List[Tuple[re.Pattern, str]] = [
    (re.compile(r"\b(?:staff|principal)\b", re.IGNORECASE), "Staff"),
    (re.compile(r"\b(?:lead|tech\s+lead|technical\s+lead)\b", re.IGNORECASE), "Lead"),
    (re.compile(r"\bsenior\b|\bsr\b", re.IGNORECASE), "Senior"),
    (re.compile(r"\b(?:mid[\s\-]?level|mid)\b", re.IGNORECASE), "Mid"),
    (re.compile(r"\b(?:junior|entry[\s\-]?level|jr\.?|associate)\b", re.IGNORECASE), "Junior"),
]


# ---------------------------------------------------------------------------
# Public result type
# ---------------------------------------------------------------------------

@dataclass
class JobStructuredFields:
    """Output of extract_job_fields(). All fields are derived — never manually edited."""

    required_skills:  List[str]        # skills before the "nice to have" boundary
    preferred_skills: List[str]        # skills after the "nice to have" boundary
    required_years:   Optional[float]  # minimum years of experience (None = not specified)
    normalized_title: str              # canonical role slug e.g. "frontend_engineer"
    seniority:        Optional[str]    # "Junior" | "Mid" | "Senior" | "Lead" | "Staff" | None
    parser_version:   str = JOB_PARSER_VERSION


# ---------------------------------------------------------------------------
# SkillExtractor
# ---------------------------------------------------------------------------

class SkillExtractor:
    """
    Splits a job description into a required section and a preferred section,
    then extracts skill tokens from each using the tech_aliases dictionary.

    Uses the same `extract_fallback_skills` approach already present in
    `nodes/extract_jd.py` as its scanning mechanism — no duplication of logic.
    """

    def __init__(self) -> None:
        self._aliases: Optional[Dict[str, str]] = None

    def _get_aliases(self) -> Dict[str, str]:
        if self._aliases is None:
            try:
                from app.nodes.normalize import get_tech_aliases
                self._aliases = get_tech_aliases()
            except Exception:
                self._aliases = {}
        return self._aliases

    def extract(self, description: str) -> Tuple[List[str], List[str]]:
        """
        Returns (required_skills, preferred_skills).

        Splits the description at the first "nice to have" / "preferred" marker.
        Everything before → required section; everything after → preferred section.
        """
        if not description:
            return [], []

        split = _PREFERRED_SECTION_PATTERN.search(description)
        if split:
            required_text  = description[: split.start()]
            preferred_text = description[split.start() :]
        else:
            required_text  = description
            preferred_text = ""

        required_skills  = self._scan_skills(required_text)
        preferred_skills = self._scan_skills(preferred_text) if preferred_text else []

        # Deduplicate: remove from preferred anything already in required
        required_set = set(s.lower() for s in required_skills)
        preferred_skills = [s for s in preferred_skills if s.lower() not in required_set]

        return required_skills, preferred_skills

    def _scan_skills(self, text: str) -> List[str]:
        """Extract skill names from text using tech_aliases and a common-terms list."""
        if not text:
            return []

        aliases = self._get_aliases()
        found: Set[str] = set()
        text_lower = text.lower()

        # Match alias keys (variant forms) and map to canonical value
        for alias, canonical in aliases.items():
            if re.search(r"\b" + re.escape(alias.lower()) + r"\b", text_lower):
                found.add(canonical)
            if re.search(r"\b" + re.escape(canonical.lower()) + r"\b", text_lower):
                found.add(canonical)

        # Supplement with a curated common-terms list for aliases not yet in tech_aliases.json
        _COMMON = [
            "python", "java", "javascript", "typescript", "go", "rust", "c++", "c#",
            "react", "vue", "angular", "node.js", "next.js", "fastapi", "django", "flask",
            "spring", "spring boot", "express",
            "aws", "gcp", "azure", "docker", "kubernetes", "terraform", "ansible",
            "postgresql", "mysql", "mongodb", "redis", "elasticsearch", "kafka",
            "git", "linux", "sql", "rest api", "graphql",
            "machine learning", "deep learning", "nlp", "pytorch", "tensorflow",
            "llm", "rag", "langchain", "langgraph",
            "ci/cd", "jenkins", "github actions",
        ]
        for term in _COMMON:
            if re.search(r"\b" + re.escape(term) + r"\b", text_lower):
                found.add(term)

        return sorted(found)


# ---------------------------------------------------------------------------
# ExperienceExtractor
# ---------------------------------------------------------------------------

class ExperienceExtractor:
    """
    Regex-based parser for minimum years of experience.

    Scans for the most specific pattern first.
    For range patterns ("5-7 years") returns the lower bound.
    Returns None when no requirement is found.
    """

    def extract(self, description: str) -> Optional[float]:
        if not description:
            return None

        for pattern in _EXPERIENCE_PATTERNS:
            m = pattern.search(description)
            if m:
                try:
                    years = float(m.group(1))
                    if 0 < years <= 40:   # sanity bounds
                        return years
                except (ValueError, IndexError):
                    continue

        return None


# ---------------------------------------------------------------------------
# TitleNormalizer
# ---------------------------------------------------------------------------

class TitleNormalizer:
    """
    Maps a raw job title to a canonical role slug using title_aliases.json.

    Lookup strategy:
      1. Check if the lowercased title belongs to any equivalency group.
      2. If not, strip seniority qualifiers and retry.
      3. Fall back to a slug derived from the raw title.

    The slug is stored on JobORM.normalized_title and used by title_matcher.py
    for similarity scoring.
    """

    def __init__(self) -> None:
        self._groups: Optional[Dict[str, List[str]]] = None

    def _get_groups(self) -> Dict[str, List[str]]:
        if self._groups is None:
            try:
                import json
                base = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
                path = os.path.join(base, "data", "title_aliases.json")
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._groups = data.get("groups", {})
            except Exception as e:
                logger.warning(f"TitleNormalizer: could not load title_aliases.json: {e}")
                self._groups = {}
        return self._groups

    def normalize(self, title: str) -> str:
        """Return the canonical slug for a job title, e.g. 'frontend_engineer'."""
        if not title:
            return "unknown"

        groups = self._get_groups()
        title_lower = title.lower().strip()

        # Strip leading seniority qualifiers for a cleaner comparison
        stripped = re.sub(
            r"^(?:senior|sr\.?\s+|junior|jr\.?\s+|lead\s+|staff\s+|principal\s+|mid[\s\-]level\s+)",
            "",
            title_lower,
            flags=re.IGNORECASE,
        ).strip()

        for canonical, variants in groups.items():
            variants_lower = [v.lower() for v in variants]
            if title_lower in variants_lower or stripped in variants_lower:
                return canonical

        # No match — generate a stable slug from the raw title
        slug = re.sub(r"[^a-z0-9]+", "_", stripped).strip("_")
        return slug or "unknown"


# ---------------------------------------------------------------------------
# SeniorityDetector
# ---------------------------------------------------------------------------

class SeniorityDetector:
    """
    Extracts seniority level from job title and description.

    Title takes precedence over description. Returns None when not determinable.
    """

    def detect(self, title: str, description: str) -> Optional[str]:
        for pattern, level in _SENIORITY_MAP:
            if pattern.search(title or ""):
                return level

        # Fall back to description only if title gave nothing
        desc_sample = (description or "")[:500]   # scan only the header area
        for pattern, level in _SENIORITY_MAP:
            if pattern.search(desc_sample):
                return level

        return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

_skill_extractor    = SkillExtractor()
_experience_extractor = ExperienceExtractor()
_title_normalizer   = TitleNormalizer()
_seniority_detector = SeniorityDetector()


def extract_job_fields(title: str, description: str) -> JobStructuredFields:
    """
    Public entry point — orchestrates the 4 internal extractors.

    Args:
        title:       Raw job title from the aggregator/connector.
        description: Plain-text job description (HTML already stripped by ingestion pipeline).

    Returns:
        JobStructuredFields with all derived fields populated.
        All fields are safe to store directly on JobORM; none require manual review.
    """
    required_skills, preferred_skills = _skill_extractor.extract(description)
    required_years   = _experience_extractor.extract(description)
    normalized_title = _title_normalizer.normalize(title)
    seniority        = _seniority_detector.detect(title, description)

    logger.debug(
        "job_parser: title=%r → %r | seniority=%s | exp=%s yrs | "
        "required=%d skills | preferred=%d skills",
        title, normalized_title, seniority, required_years,
        len(required_skills), len(preferred_skills),
    )

    return JobStructuredFields(
        required_skills=required_skills,
        preferred_skills=preferred_skills,
        required_years=required_years,
        normalized_title=normalized_title,
        seniority=seniority,
        parser_version=JOB_PARSER_VERSION,
    )
