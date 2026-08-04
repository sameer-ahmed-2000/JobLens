import logging
from typing import Dict, Any
from app.services.similarity import cosine_similarity, hybrid_score, rank_postings
from app.config import settings

logger = logging.getLogger(__name__)

# Scoring version produced by this implementation of the score node.
# Bump to "v3" when LLM reranking (Phase 4) is enabled.
SCORING_VERSION = "v2"


def score_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    LangGraph node — scores and ranks postings against the resume embedding.

    Scoring formula (hybrid, Phase 2+):
        Final = w_semantic  * cosine_similarity
              + w_skill     * skill_match_score
              + w_title     * title_similarity
              + w_experience * experience_score
              − missing_required_skill_count * penalty_per_skill

    Structured fields (required_skills, normalized_title, experience_required)
    are read from the database where available (populated by embedding_worker
    via job_parser). Jobs not yet processed by the parser fall back to neutral
    stub values (skill=0.5, title=0.5, experience=1.0) so ranking degrades
    gracefully rather than erroring.

    All weights are configurable via .env (SCORING_WEIGHT_SEMANTIC, etc.).
    """
    logger.info("Executing score_node (hybrid scoring v2)...")
    postings = state.get("postings", [])
    posting_embeddings = state.get("posting_embeddings", [])
    user_id = state.get("user_id", "default-user-id")

    # ---- Load active resume embedding + metadata ----
    resume_embedding = None
    resume_title = ""
    resume_years = 0.0
    resume_skills = set()
    resume_project_techs = set()
    resume_text = ""

    try:
        from app.repositories.uow import UnitOfWork
        from app.nodes.normalize import get_tech_aliases
        from app.nodes.normalize_skills import normalize_skill_name
        
        aliases = get_tech_aliases()

        with UnitOfWork() as uow:
            active_resume = uow.resumes.get_active(user_id)
            if active_resume and active_resume.get("embedding") is not None:
                resume_embedding = active_resume["embedding"]
                resume_title = active_resume.get("title", "")
                resume_years = float(active_resume.get("years_experience", 0) or 0)
                for s in active_resume.get("skills", []):
                    resume_skills.add(s.lower())
                    norm_s = normalize_skill_name(s, aliases).lower()
                    if norm_s:
                        resume_skills.add(norm_s)
                for p in active_resume.get("projects", []):
                    for t in p.get("technologies", []):
                        resume_project_techs.add(t.lower())
                        norm_t = normalize_skill_name(t, aliases).lower()
                        if norm_t:
                            resume_project_techs.add(norm_t)
                raw = active_resume.get("raw_text", "") or ""
                resume_text = (
                    resume_title + " " +
                    " ".join(active_resume.get("skills", [])) + " " +
                    raw[:1000]
                ).lower()
                logger.info(f"Loaded active resume from database for user {user_id}.")
    except Exception as e:
        logger.warning(f"Could not load active resume from DB: {e}; falling back to local file.")


    # Fallback to local file-based resume index
    if resume_embedding is None:
        logger.info("Falling back to local file resume index for embedding...")
        from app.services.resume_index import resume_index
        from app.nodes.normalize import get_tech_aliases
        from app.nodes.normalize_skills import normalize_skill_name
        
        aliases = get_tech_aliases()
        resume_embedding = resume_index.get_primary_embedding()
        resume_data = resume_index.get_resume_data()
        resume_title = resume_data.get("title", "")
        resume_years = float(resume_data.get("years_experience", 0) or 0)
        for s in resume_data.get("skills", []):
            resume_skills.add(s.lower())
            norm_s = normalize_skill_name(s, aliases).lower()
            if norm_s:
                resume_skills.add(norm_s)

    if not postings or not posting_embeddings or resume_embedding is None:
        logger.warning("Missing postings, embeddings, or resume embedding for scoring.")
        return {"scored_postings": []}

    if len(postings) != len(posting_embeddings):
        logger.error(f"Length mismatch: {len(postings)} postings vs {len(posting_embeddings)} embeddings")
        return {"scored_postings": []}

    # ---- Import SkillMatcher and title_matcher ----
    from app.services.skill_matcher import SkillMatcher
    from app.services.title_matcher import title_similarity

    skill_matcher_inst = SkillMatcher()

    # ---- Score each posting with the hybrid formula ----
    from app.models.schemas import ScoredPosting
    scored = []

    try:
        from app.repositories.uow import UnitOfWork
        db_available = True
    except Exception:
        db_available = False

    for posting, emb in zip(postings, posting_embeddings):
        # 1. Semantic similarity (always available)
        sem_sim = cosine_similarity(emb, resume_embedding)

        # 2. Load structured fields from DB (may be None for unparsed jobs)
        structured = None
        if db_available:
            try:
                with UnitOfWork() as uow:
                    structured = uow.jobs.get_structured_fields(posting.id)
            except Exception as e:
                logger.debug(f"score_node: could not load structured fields for {posting.id}: {e}")

        # 3. Skill match score
        if structured and structured.get("required_skills"):
            match_result = skill_matcher_inst.match(
                required_skills=structured["required_skills"],
                resume_skills=resume_skills,
                resume_project_techs=resume_project_techs,
                resume_text=resume_text,
            )
            skill_score = match_result.score
            missing_required_count = len(match_result.missing_required)
        else:
            # Neutral stub — structured fields not yet populated for this job
            skill_score = 0.5
            missing_required_count = 0

        # 4. Title similarity
        job_title = structured.get("title", posting.title) if structured else posting.title
        title_score = title_similarity(resume_title, job_title) if resume_title else 0.5

        # 5. Experience score
        required_years = structured.get("experience_required") if structured else None
        exp_score = SkillMatcher.experience_score(resume_years, required_years)

        # 6. Compute hybrid score → ScoreBreakdown
        breakdown = hybrid_score(
            semantic_sim=sem_sim,
            skill_score=skill_score,
            title_score=title_score,
            experience_score=exp_score,
            missing_required_count=missing_required_count,
            weights=settings,
        )

        scored_posting = ScoredPosting(
            posting=posting,
            overall_score=breakdown.final,
            fit_rationale="Pending analysis...",
            score_breakdown=breakdown,
        )
        scored.append(scored_posting)

    # Deterministic sort: final score desc → title asc → id asc
    scored.sort(key=lambda sp: (-sp.overall_score, sp.posting.title, sp.posting.id))
    logger.info(f"score_node: hybrid-ranked {len(scored)} postings (scoring_version={SCORING_VERSION}).")
    return {"scored_postings": scored, "scoring_version": SCORING_VERSION}
