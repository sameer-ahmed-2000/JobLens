import time
import logging
from typing import Optional
from fastapi import HTTPException
from app.models.schemas import GapReport, GapReportRequest
from app.graphs.gap_graph import gap_graph
from app.nodes.fetch import fetch_postings
from app.repositories.uow import UnitOfWork

logger = logging.getLogger("gap_service")

class GapService:
    async def analyze_gap(self, request: GapReportRequest) -> GapReport:
        """Execute the LangGraph Gap Analyzer workflow and return a structured GapReport."""
        logger.info("Gap Analysis Started")
        t0 = time.perf_counter()

        jd_text: Optional[str] = request.jd_text or request.job_description
        job_title = "Target Role"
        company = "Target Company"
        matched_job_id: Optional[str] = None
        user_id = "default-user-id"
        resume_ver = 1

        if request.posting_url:
            logger.info(f"Loading job posting from URL/ID: {request.posting_url}")
            try:
                with UnitOfWork() as uow:
                    matched_posting = uow.jobs.get_by_id_or_url(request.posting_url)
                    if matched_posting:
                        matched_job_id = matched_posting.id
                        jd_text = matched_posting.description
                        job_title = matched_posting.title
                        company = matched_posting.company
                        
                        # Check resume version
                        res = uow.resumes.get_by_user_id(user_id)
                        if res and "version" in res:
                            resume_ver = res["version"] or 1

                        # Check for cached gap report
                        cached_report = uow.gaps.get_cached_report(matched_job_id, user_id, resume_ver)
                        if cached_report:
                            logger.info(f"Returning cached Gap Report for job {matched_job_id} (resume version {resume_ver}).")
                            return cached_report
            except Exception as e:
                logger.warning(f"Database lookup failed for job posting {request.posting_url}: {e}; falling back to fetch_postings.")

            # Fallback if DB lookup didn't match or failed
            if not matched_job_id:
                try:
                    postings = fetch_postings()
                except FileNotFoundError as e:
                    logger.error(f"Postings file not found: {e}")
                    raise HTTPException(status_code=404, detail="Job postings data file not found.")
                except Exception as e:
                    logger.error(f"Failed to load postings: {e}")
                    raise HTTPException(status_code=500, detail="Failed to load job postings.")

                for p in postings:
                    if (p.url and p.url.strip().lower() == request.posting_url.strip().lower()) or \
                       (p.id and p.id.strip().lower() == request.posting_url.strip().lower()):
                        jd_text = p.description
                        job_title = p.title
                        company = p.company
                        matched_job_id = p.id
                        break

            if not matched_job_id and not jd_text:
                logger.warning(f"Job posting not found for url/id: {request.posting_url}")
                raise HTTPException(status_code=404, detail=f"Job posting not found for URL or ID: {request.posting_url}")

        if not jd_text or not jd_text.strip():
            logger.warning("No valid job description text or URL provided.")
            raise HTTPException(status_code=400, detail="Either a valid posting_url or jd_text (or job_description) must be provided.")

        try:
            state_input = {
                "jd_text": jd_text,
                "job_title": job_title,
                "company": company
            }
            state = gap_graph.invoke(state_input)
        except FileNotFoundError as e:
            logger.error(f"Gap Analysis failed (File not found): {e}")
            raise HTTPException(status_code=404, detail=f"Data file missing: {str(e)}")
        except ValueError as e:
            logger.error(f"Gap Analysis failed (Validation error): {e}")
            raise HTTPException(status_code=400, detail=str(e))
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Gap Analysis failed unexpectedly: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Internal server error during gap analysis pipeline execution.")

        elapsed = time.perf_counter() - t0
        report = state.get("gap_report")
        if not report:
            logger.error("Gap Analysis pipeline finished without generating a GapReport.")
            raise HTTPException(status_code=500, detail="Failed to generate gap report.")

        # Save generated report to database if linked to a job
        if matched_job_id:
            try:
                with UnitOfWork() as uow:
                    uow.gaps.save_report(job_id=matched_job_id, user_id=user_id, resume_version=resume_ver, report=report)
                    uow.commit()
                    logger.info(f"Saved Gap Report to database for job {matched_job_id}.")
            except Exception as e:
                logger.warning(f"Could not save Gap Report to database: {e}")

        logger.info("Gap Analysis Complete")
        logger.info(f"Total execution time: {elapsed:.2f} s")
        return report

# Singleton instance
gap_service = GapService()
