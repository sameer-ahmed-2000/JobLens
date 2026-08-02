"""
LLM Router Factory
------------------
Returns one cached LLMRouter instance per role so each of the 4 roles gets a
stable, independently-configured router without re-resolving provider settings
or reconnecting on every call.

Usage:
    from app.services.llm_router_factory import get_llm_router

    router = get_llm_router("rationale")
    result = router.generate(prompt=...)

Valid roles: "rationale", "gap_analysis", "resume_parsing", "notification"
"""
from functools import lru_cache
from app.services.llm_router import LLMRouter


@lru_cache(maxsize=None)
def get_llm_router(role: str) -> LLMRouter:
    """
    Return a cached LLMRouter for the given role.

    lru_cache is safe here because:
    - Roles are a small, fixed set (4 values).
    - Provider config is read from environment at process start and does not
      change at runtime; a restart naturally clears the cache.
    """
    return LLMRouter(role=role)
