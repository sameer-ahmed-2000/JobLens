"""
Tests for llm_router_factory.py

Verifies:
1. lru_cache returns the SAME instance for repeated calls to the same role.
2. Different roles return DIFFERENT instances.
3. Each instance carries the correct role attribute.
4. Per-role provider resolution: when env vars differ per role, the resolved
   provider names differ accordingly.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import logging
import pytest
from unittest.mock import patch
from functools import lru_cache

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s - %(message)s")
logger = logging.getLogger("test_llm_router_factory")


def _clear_factory_cache():
    """Clear the lru_cache between tests so env-var patches take effect."""
    from app.services import llm_router_factory
    llm_router_factory.get_llm_router.cache_clear()


def test_cache_returns_same_instance_for_same_role():
    """Repeated calls for the same role must return the identical object (lru_cache identity)."""
    _clear_factory_cache()
    from app.services.llm_router_factory import get_llm_router

    router_a = get_llm_router("rationale")
    router_b = get_llm_router("rationale")
    assert router_a is router_b, (
        "lru_cache should return the same LLMRouter instance for the same role; "
        "got two different objects — the cache is not working."
    )
    logger.info("PASS: lru_cache returns same instance for same role.")


def test_different_roles_return_different_instances():
    """Different roles must return independent router instances."""
    _clear_factory_cache()
    from app.services.llm_router_factory import get_llm_router

    rationale_router = get_llm_router("rationale")
    gap_router = get_llm_router("gap_analysis")
    assert rationale_router is not gap_router, (
        "Different roles should produce different LLMRouter instances."
    )
    logger.info("PASS: Different roles return different instances.")


def test_router_carries_correct_role():
    """Each router's .role attribute matches the key it was created with."""
    _clear_factory_cache()
    from app.services.llm_router_factory import get_llm_router

    for role in ["rationale", "gap_analysis", "resume_parsing", "notification"]:
        router = get_llm_router(role)
        assert router.role == role, (
            f"Expected router.role == '{role}', got '{router.role}'."
        )
    logger.info("PASS: All routers carry the correct role attribute.")


def test_per_role_provider_resolution():
    """
    When LLM_PROVIDER_RATIONALE=groq and LLM_PROVIDER_GAP_ANALYSIS=gemini are set,
    the two routers should resolve to different requested_provider values.
    """
    from app.config import settings
    from app.services.llm_router import LLMRouter

    with patch.object(settings, "llm_provider_rationale", "groq"), \
         patch.object(settings, "groq_api_key", "test-groq-key"), \
         patch.object(settings, "llm_provider_gap_analysis", "gemini"), \
         patch.object(settings, "gemini_api_key", "test-gemini-key"):

        rationale_router = LLMRouter(role="rationale")
        gap_router = LLMRouter(role="gap_analysis")

        assert rationale_router.requested_provider == "groq", (
            f"Expected rationale to use 'groq', got '{rationale_router.requested_provider}'"
        )
        assert gap_router.requested_provider == "gemini", (
            f"Expected gap_analysis to use 'gemini', got '{gap_router.requested_provider}'"
        )
        assert rationale_router.requested_provider != gap_router.requested_provider, (
            "rationale and gap_analysis should have different providers."
        )

    logger.info("PASS: Per-role provider resolution works correctly.")


def test_legacy_llm_provider_fallback():
    """
    If no role-specific vars are set but the legacy LLM_PROVIDER default is freemodel,
    all roles should fall back to freemodel.
    """
    from app.config import settings
    from app.services.llm_router import LLMRouter

    with patch.object(settings, "llm_provider_default", "freemodel"), \
         patch.object(settings, "freemodel_api_key", "test-freemodel-key"), \
         patch.object(settings, "llm_provider_rationale", ""):

        router = LLMRouter(role="rationale")
        assert router.requested_provider == "freemodel", (
            f"Legacy default 'freemodel' should apply when role var is empty, "
            f"got '{router.requested_provider}'"
        )

    logger.info("PASS: Legacy LLM_PROVIDER env var correctly falls back as default.")


if __name__ == "__main__":
    test_cache_returns_same_instance_for_same_role()
    test_different_roles_return_different_instances()
    test_router_carries_correct_role()
    test_per_role_provider_resolution()
    test_legacy_llm_provider_fallback()
    logger.info("=== All llm_router_factory tests passed! ===")
