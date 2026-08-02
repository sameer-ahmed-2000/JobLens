"""
Live smoke test for all three LLM providers: freemodel, groq, gemini.
Tests both generate() (text) and generate_json() (structured output) for each.
Run from backend/ directory.
"""
import os, sys, json, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Force UTF-8 output so Unicode in LLM responses doesn't crash on Windows charmap
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from app.config import settings
from app.services.llm_router import LLMRouter, OpenAICompatibleBackend

PROVIDERS = ["freemodel", "groq", "gemini"]

JD_SNIPPET = (
    "We are looking for a Senior Python Engineer with FastAPI, PostgreSQL, "
    "Redis, Docker, and experience with LLM/RAG pipelines. Nice to have: React, AWS."
)

TEXT_PROMPT = (
    "Resume Skills: Python, FastAPI, PostgreSQL, Docker, LangGraph\n"
    "Job Title: Senior Python Engineer at TechCorp\n"
    "Job Description: " + JD_SNIPPET[:200] + "\n\n"
    "Write ONE sentence (max 25 words) about the candidate's fit. "
    "Mention only overlapping skills. Do not invent experience."
)

JSON_PROMPT = (
    "You are an expert HR recruiter.\n"
    "Analyze the following Job Description and extract requirements.\n"
    "Return ONLY valid JSON matching this exact schema:\n"
    '{"required_skills": ["skill1"], "nice_to_have_skills": ["skill3"], '
    '"seniority_level": "Senior", "key_responsibilities": ["resp1"]}\n\n'
    "Job Description:\n" + JD_SNIPPET
)

PASS = "\033[92mPASS\033[0m"
FAIL = "\033[91mFAIL\033[0m"

results = {}

for provider in PROVIDERS:
    print(f"\n{'='*60}")
    print(f"  PROVIDER: {provider.upper()}")
    print(f"{'='*60}")

    router = LLMRouter(role="gap_analysis", provider_override=provider)
    print(f"  requested={router.requested_provider}  active={router.active_provider}")
    print(f"  backend: {type(router._backend).__name__}")
    if hasattr(router._backend, "base_url"):
        print(f"  base_url: {router._backend.base_url}")

    provider_results = {"generate": False, "generate_json": False, "degraded": False}

    if router.active_provider != provider:
        print(f"  [{FAIL}] Provider degraded to '{router.active_provider}' — key missing or invalid.")
        provider_results["degraded"] = True
        results[provider] = provider_results
        continue

    # --- Test 1: generate() ---
    print(f"\n  [generate] Sending text prompt...")
    t0 = time.time()
    try:
        text_result = router.generate(prompt=TEXT_PROMPT)
        elapsed = time.time() - t0
        if text_result and text_result != "Rationale unavailable.":
            safe = text_result[:120].encode("ascii", errors="replace").decode()
            print(f"  [{PASS}] ({elapsed:.1f}s) -> {safe}")
            provider_results["generate"] = True
        else:
            print(f"  [{FAIL}] Returned fallback string: '{text_result}'")
    except Exception as e:
        print(f"  [{FAIL}] Exception: {e}")

    # --- Test 2: generate_json() ---
    print(f"\n  [generate_json] Sending structured JSON prompt...")
    t0 = time.time()
    try:
        json_result = router.generate_json(prompt=JSON_PROMPT)
        elapsed = time.time() - t0
        if json_result and isinstance(json_result, dict):
            skills = json_result.get("required_skills", [])
            seniority = json_result.get("seniority_level", "?")
            print(f"  [{PASS}] ({elapsed:.1f}s) seniority='{seniority}' required_skills={skills[:4]}")
            # Validate expected structure
            assert isinstance(skills, list) and len(skills) > 0, "required_skills is empty"
            assert "seniority_level" in json_result, "seniority_level missing"
            assert "key_responsibilities" in json_result, "key_responsibilities missing"
            provider_results["generate_json"] = True
        else:
            print(f"  [{FAIL}] Returned None or non-dict: {json_result}")
    except AssertionError as e:
        print(f"  [{FAIL}] Schema validation: {e}")
    except Exception as e:
        print(f"  [{FAIL}] Exception: {e}")

    results[provider] = provider_results

# --- Summary ---
print(f"\n{'='*60}")
print("  SUMMARY")
print(f"{'='*60}")
all_passed = True
for provider, r in results.items():
    gen_ok = r["generate"]
    json_ok = r["generate_json"]
    degraded = r["degraded"]
    status = "DEGRADED" if degraded else ("ALL PASS" if gen_ok and json_ok else "PARTIAL/FAIL")
    print(f"  {provider:<12} generate={gen_ok}  generate_json={json_ok}  status={status}")
    if not (gen_ok and json_ok and not degraded):
        all_passed = False

print()
if all_passed:
    print("  All three providers verified end-to-end.")
else:
    print("  One or more providers failed — see details above.")
    sys.exit(1)
