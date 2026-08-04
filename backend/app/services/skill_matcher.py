"""
SkillMatcher — reusable, numeric skill-matching service.

Extracts the deterministic matching core from compare_skills_node so it can be
consumed by discovery scoring, gap analysis, notifications, and future features
without any LangGraph or presentation-layer coupling.

Architecture:
    SkillMatcher
    ├── Discovery ranking  (nodes/score.py)
    ├── Gap analysis        (nodes/compare_skills.py — refactored to delegate here)
    ├── Notifications       (future)
    └── Interview coach     (future)
"""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set

logger = logging.getLogger(__name__)


@dataclass
class SkillMatchResult:
    """Numeric outcome of matching required skills against a resume."""

    matched: int                         # skills classified "have"
    partial: int                         # skills classified "partial" (transferable)
    missing_required: List[str]          # skills classified "missing"
    total: int                           # total required skills evaluated
    score: float                         # (matched + 0.5 * partial) / total  ∈ [0, 1]
    matched_skills: List[str] = field(default_factory=list)
    partial_skills: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Transferable technology clusters
# Mirrors the clusters in compare_skills.py — single source of truth here.
# ---------------------------------------------------------------------------
TRANSFERABLE_CLUSTERS: List[Set[str]] = [
    {"python", "fastapi", "django", "flask", "node.js", "express", "backend", "api", "rest api"},
    {"react", "vue.js", "angular", "next.js", "typescript", "javascript", "frontend", "web development"},
    {
        "langgraph", "langchain", "llama index", "rag", "llm", "ai", "genai",
        "generative ai", "machine learning", "deep learning", "nlp", "pytorch",
        "tensorflow", "openai", "huggingface", "vector database", "faiss", "pinecone", "qdrant",
    },
    {"aws", "gcp", "azure", "cloud", "cloud computing"},
    {"docker", "kubernetes", "k8s", "containerization", "docker compose"},
    {"kafka", "rabbitmq", "event streaming", "distributed systems", "pub/sub", "streaming"},
    {"postgresql", "mysql", "mongodb", "sqlite", "redis", "dynamodb", "sql", "nosql", "database"},
]

# Words excluded from "word-overlap" partial matching to avoid false positives
_STOP_WORDS: frozenset = frozenset(
    {"and", "the", "with", "using", "for", "from", "system", "systems", "development"}
)


class SkillMatcher:
    """
    Pure, stateless skill matcher.  No IO, no LangGraph, no side effects.

    All matching logic is deterministic:
      1. Direct match  — exact string or substring equality after normalisation
      2. Partial match — same technology cluster (transferable skills)
      3. Partial match — significant word overlap in resume text
    """

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def match(
        self,
        required_skills: List[str],
        resume_skills: Set[str],
        resume_project_techs: Set[str],
        resume_text: str,
        aliases: Optional[Dict[str, str]] = None,
    ) -> SkillMatchResult:
        """
        Match *required_skills* against the candidate's knowledge base.

        Args:
            required_skills:      Skills extracted from a job description.
            resume_skills:        Normalised skills from the resume's skills list.
            resume_project_techs: Normalised techs from all listed projects.
            resume_text:          Full lowercase text of the resume for word-overlap fallback.
            aliases:              Optional tech-alias map (canonical → canonical).

        Returns:
            SkillMatchResult with a numeric score in [0, 1].
        """
        if not required_skills:
            return SkillMatchResult(
                matched=0, partial=0, missing_required=[], total=0, score=1.0
            )

        direct_match_set: Set[str] = resume_skills | resume_project_techs

        matched_skills: List[str] = []
        partial_skills: List[str] = []
        missing_required: List[str] = []

        for req_skill in required_skills:
            req_lower = req_skill.lower().strip()
            classification = self._classify(req_lower, direct_match_set, resume_text)

            if classification == "have":
                matched_skills.append(req_skill)
            elif classification == "partial":
                partial_skills.append(req_skill)
            else:
                missing_required.append(req_skill)

        total = len(required_skills)
        matched = len(matched_skills)
        partial = len(partial_skills)

        # Partial matches are worth half a direct match
        raw_score = (matched + 0.5 * partial) / total if total > 0 else 1.0
        score = round(min(1.0, max(0.0, raw_score)), 4)

        result = SkillMatchResult(
            matched=matched,
            partial=partial,
            missing_required=missing_required,
            total=total,
            score=score,
            matched_skills=matched_skills,
            partial_skills=partial_skills,
        )
        logger.debug(
            "SkillMatcher: %d have, %d partial, %d missing → score=%.4f",
            matched, partial, len(missing_required), score,
        )
        return result

    @staticmethod
    def experience_score(resume_years: float, required_years: Optional[float]) -> float:
        """
        Smooth, non-binary experience compatibility score.

        Rules:
        - If ``required_years`` is None  → 1.0 (neutral; no requirement)
        - If resume meets or exceeds req → 1.0  (capped; 18 yrs vs 3 yrs = 1.0, same as 5 yrs)
        - Under-experience              → logistic decay; mild for small gaps, stronger for large
        - Hard floor of 0.1             → never completely eliminates a candidate

        Examples:
            experience_score(5.0, 3.0)  → 1.0   (meets requirement)
            experience_score(2.0, 3.0)  → ~0.77  (1 year short)
            experience_score(1.0, 5.0)  → ~0.43  (4 years short)
            experience_score(0.5, 15.0) → ~0.18  (severe mismatch)
            experience_score(5.0, None) → 1.0   (no requirement)
        """
        if required_years is None:
            return 1.0
        if resume_years >= required_years:
            return 1.0
        gap = required_years - resume_years
        # Logistic decay: 1 / (1 + k*gap), k=0.3 gives a smooth curve
        return round(max(0.1, 1.0 / (1.0 + 0.3 * gap)), 4)

    # ------------------------------------------------------------------
    # Internal classification logic
    # ------------------------------------------------------------------

    @staticmethod
    def _classify(
        req_lower: str,
        direct_match_set: Set[str],
        resume_text: str,
    ) -> str:
        """Returns 'have', 'partial', or 'missing'."""

        # ---- 1. Direct match ----
        if req_lower in direct_match_set:
            return "have"

        # Candidate skill is a substring of the required skill (e.g. "aws" in "aws lambda")
        for cand_s in direct_match_set:
            if len(cand_s) >= 3 and (
                cand_s == req_lower
                or f" {cand_s} " in f" {req_lower} "
                or cand_s in req_lower.split()
            ):
                return "have"

        # Required skill is a substring of a candidate skill
        for cand_s in direct_match_set:
            if len(req_lower) >= 3 and req_lower in cand_s:
                return "have"

        # ---- 2. Transferable cluster (partial) ----
        for cluster in TRANSFERABLE_CLUSTERS:
            if any(c == req_lower or c in req_lower.split() for c in cluster):
                if any(c in direct_match_set for c in cluster):
                    return "partial"

        # ---- 3. Word-overlap in resume text (partial) ----
        words = [
            w for w in req_lower.split()
            if len(w) >= 3 and w not in _STOP_WORDS
        ]
        if words and any(w in resume_text for w in words):
            return "partial"

        return "missing"


# ---------------------------------------------------------------------------
# Module-level singleton (stateless — safe to share across threads)
# ---------------------------------------------------------------------------
skill_matcher = SkillMatcher()
