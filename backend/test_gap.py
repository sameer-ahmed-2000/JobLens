import os
import sys
import asyncio
import logging
from fastapi import HTTPException
from unittest.mock import patch

# Ensure backend directory is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s - %(message)s")
logger = logging.getLogger("test_gap")

def test_node_step_by_step():
    logger.info("=== Starting Step-by-Step Node Verification ===")
    from app.nodes.extract_jd import extract_jd_node
    from app.nodes.normalize_skills import normalize_skills_node
    from app.nodes.compare_skills import compare_skills_node
    from app.nodes.bridge_generator import bridge_generator_node
    from app.nodes.generate_report import generate_report_node

    sample_jd = """
    We are looking for a Senior AI Engineer to join our team.
    Responsibilities:
    - Build scalable LLM applications and RAG pipelines.
    - Deploy APIs and services.
    Requirements:
    - Strong proficiency in Python and Fast API.
    - Hands-on experience with LangGraph or LangChain.
    - Experience with Kubernetes and Docker is required.
    - Nice to have: experience with vector databases like Qdrant or Pinecone.
    """

    state = {"jd_text": sample_jd, "job_title": "Senior AI Engineer", "company": "TechCorp"}

    # 1. Extract JD
    state.update(extract_jd_node(state))
    extracted = state.get("extracted_jd")
    assert extracted is not None, "JD extraction failed to return JDRequirements."
    assert len(extracted.required_skills) > 0, "No required skills extracted."
    logger.info(f"Step 1 (Extract JD): Extracted skills: {extracted.required_skills}")

    # 2. Normalize Skills
    state.update(normalize_skills_node(state))
    norm_skills = state.get("normalized_skills", [])
    assert len(norm_skills) > 0, "Normalization failed to output skills."
    # Check that Fast API was normalized if present
    logger.info(f"Step 2 (Normalize Skills): Normalized skills: {norm_skills}")

    # 3. Compare Skills
    state.update(compare_skills_node(state))
    gaps = state.get("skill_gaps", [])
    assert len(gaps) == len(norm_skills), "Skill gaps count mismatch."
    have_count = sum(1 for g in gaps if g.classification == "have")
    partial_count = sum(1 for g in gaps if g.classification == "partial")
    missing_count = sum(1 for g in gaps if g.classification == "missing")
    logger.info(f"Step 3 (Compare Skills): {have_count} have, {partial_count} partial, {missing_count} missing.")
    for g in gaps:
        logger.info(f"   -> Skill: {g.skill} | Status: {g.classification}")

    # 4. Bridge Generator
    state.update(bridge_generator_node(state))
    for g in gaps:
        assert g.bridge_suggestion is not None, f"Bridge suggestion missing for skill {g.skill}"
        if g.classification == "partial":
            logger.info(f"Step 4 (Bridge Suggestion for {g.skill}): {g.bridge_suggestion}")

    # 5. Generate Report
    state.update(generate_report_node(state))
    report = state.get("gap_report")
    assert report is not None, "Final GapReport not generated."
    assert 0.0 <= report.match_score <= 1.0, "Match score out of bounds."
    assert report.confidence_reasoning is not None, "Confidence reasoning missing."
    logger.info(f"Step 5 (Generate Report): Match Score: {report.match_score}")
    logger.info(f"   -> Reasoning: {report.confidence_reasoning}")
    logger.info(f"   -> Summary: {report.overall_recommendation}")
    logger.info("=== Step-by-Step Node Verification Passed Successfully! ===\n")

def test_service_execution():
    logger.info("=== Starting GapService Verification ===")
    from app.services.gap_service import gap_service
    from app.models.schemas import GapReportRequest

    # Test with posting_url
    url_req = GapReportRequest(posting_url="https://example.com/jobs/1")
    report_url = asyncio.run(gap_service.analyze_gap(url_req))
    assert report_url is not None, "Service returned None for posting_url."
    assert report_url.company == "TechNova Solutions", "Company mismatch when loading from posting_url."
    logger.info(f"Service test (posting_url): Successfully generated report for {report_url.job_title} at {report_url.company} with score {report_url.match_score}")

    # Test with jd_text
    text_req = GapReportRequest(jd_text="Looking for a Python developer with React and AWS skills.")
    report_text = asyncio.run(gap_service.analyze_gap(text_req))
    assert report_text is not None, "Service returned None for jd_text."
    logger.info(f"Service test (jd_text): Successfully generated report with score {report_text.match_score}")
    logger.info("=== GapService Verification Passed Successfully! ===\n")

def test_graceful_degradation():
    logger.info("=== Starting Graceful Degradation & Error Handling Verification ===")
    from app.services.gap_service import gap_service
    from app.models.schemas import GapReportRequest
    from app.services.llm_router import llm_router

    # 1. Invalid JD text
    try:
        asyncio.run(gap_service.analyze_gap(GapReportRequest(jd_text="ab")))
        assert False, "Should have raised HTTPException for short/invalid JD text."
    except HTTPException as e:
        assert e.status_code == 400, f"Expected 400 for invalid JD text, got {e.status_code}"
        logger.info("Verified 400 error for short/invalid JD text.")

    # 2. Missing posting URL
    try:
        asyncio.run(gap_service.analyze_gap(GapReportRequest(posting_url="https://nonexistent.job/999")))
        assert False, "Should have raised HTTPException for non-existent posting URL."
    except HTTPException as e:
        assert e.status_code == 404, f"Expected 404 for missing posting URL, got {e.status_code}"
        logger.info("Verified 404 error for non-existent posting URL.")

    # 3. LLM Failure / Offline degradation test
    logger.info("Testing LLM failure fallback without crashing pipeline...")
    with patch.object(llm_router, "generate_structured_output", return_value=None), \
         patch.object(llm_router, "generate", return_value="Rationale unavailable."):
        
        req = GapReportRequest(jd_text="Seeking AI Engineer with Python, FastAPI, and AWS.")
        report = asyncio.run(gap_service.analyze_gap(req))
        assert report is not None, "Pipeline crashed when LLM was unavailable!"
        assert len(report.gaps) > 0, "Fallback extraction failed to find skills."
        assert report.overall_fit_summary == "Summary unavailable." or report.overall_fit_summary == "Rationale unavailable.", "Fallback summary mismatch."
        logger.info(f"Verified LLM offline fallback: report generated with {len(report.gaps)} skills and default summary.")

    logger.info("=== Graceful Degradation Verification Passed Successfully! ===\n")

if __name__ == "__main__":
    try:
        test_node_step_by_step()
        test_service_execution()
        test_graceful_degradation()
    except Exception as e:
        logger.error(f"Gap Verification failed: {e}", exc_info=True)
        sys.exit(1)
