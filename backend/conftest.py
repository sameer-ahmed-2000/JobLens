"""
conftest.py — shared pytest fixtures for the JobLens backend test suite.

The most critical fixture here is `clear_llm_router_cache`, which is
`autouse=True` and runs before every test function. Without it, the
`lru_cache` on `get_llm_router(role)` persists across tests: if test A
populates the cache for role "gap_analysis" with provider X, and test B
patches settings to provider Y then calls `get_llm_router("gap_analysis")`,
it will silently receive the stale test-A instance. This produces
"the test asserts groq was used but it's actually still gemini from an
earlier test" failures that are hard to reproduce and trace.

The fix is simple: always clear before each test. The cost is one
LLMRouter.__init__ call per role per test that exercises the factory —
negligible since __init__ only reads settings and picks a backend class.
"""
import pytest


@pytest.fixture(autouse=True)
def clear_llm_router_cache():
    """
    Clear the get_llm_router lru_cache before every test.

    autouse=True ensures this runs automatically for every test in the
    suite without needing to declare it as a parameter. The cache is also
    cleared after the test (via yield) so that tests which deliberately
    exercise caching don't leak state to the next test.
    """
    from app.services import llm_router_factory
    llm_router_factory.get_llm_router.cache_clear()
    yield
    llm_router_factory.get_llm_router.cache_clear()
