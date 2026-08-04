"""
backfill_job_parser.py — one-time backfill of structured fields for existing jobs.

Populates required_skills, preferred_skills, normalized_title, seniority,
experience_required, and job_parser_version for all jobs that were ingested before
Phase 3 of the hybrid scoring rollout.

After running this script, all jobs will have structured fields available for
hybrid scoring. New jobs ingested after Phase 3 deployment are automatically
parsed by the embedding_worker.

Usage:
    # From backend/ directory:
    python backfill_job_parser.py

    # Dry run (preview counts without writing):
    python backfill_job_parser.py --dry-run

    # Limit to a subset (useful for staged rollout):
    python backfill_job_parser.py --limit 500

    # Force reprocess even jobs already at the current parser version:
    python backfill_job_parser.py --force

After the backfill, run score_all_jobs_for_user for each active user to
regenerate hybrid match scores against the now-populated structured fields.
"""
import argparse
import logging
import sys
import os

# Ensure the backend package is importable regardless of working directory
sys.path.insert(0, os.path.dirname(__file__))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("backfill_job_parser")


def run_backfill(dry_run: bool = False, limit: int = 0, force: bool = False) -> None:
    from app.services.job_parser import extract_job_fields, JOB_PARSER_VERSION
    from app.repositories.uow import UnitOfWork
    from app.models.orm import JobORM

    logger.info(
        f"Starting job parser backfill "
        f"(dry_run={dry_run}, limit={limit or 'all'}, force={force}, "
        f"parser_version={JOB_PARSER_VERSION})"
    )

    # Query jobs that need (re)processing
    with UnitOfWork() as uow:
        q = uow.session.query(JobORM.id, JobORM.title, JobORM.description, JobORM.job_parser_version)
        if not force:
            # Skip jobs already on the current parser version
            q = q.filter(
                (JobORM.job_parser_version == None) |  # noqa: E711
                (JobORM.job_parser_version != JOB_PARSER_VERSION)
            )
        if limit > 0:
            q = q.limit(limit)
        jobs = q.all()

    total = len(jobs)
    logger.info(f"Found {total} job(s) to process.")

    if dry_run:
        logger.info(f"[DRY RUN] Would process {total} job(s). No changes written.")
        return

    processed = 0
    failed = 0

    for job_id, title, description, existing_version in jobs:
        try:
            structured = extract_job_fields(title or "", description or "")

            with UnitOfWork() as uow:
                job = uow.session.query(JobORM).filter(JobORM.id == job_id).first()
                if not job:
                    logger.warning(f"Job {job_id} disappeared between query and update — skipping.")
                    continue

                job.required_skills    = structured.required_skills
                job.preferred_skills   = structured.preferred_skills
                job.normalized_title   = structured.normalized_title
                job.seniority          = structured.seniority
                if structured.required_years is not None:
                    job.experience_required = structured.required_years
                job.job_parser_version = structured.parser_version
                uow.commit()

            processed += 1
            if processed % 100 == 0:
                logger.info(f"Progress: {processed}/{total} jobs processed...")

        except Exception as e:
            logger.error(f"Failed to process job {job_id} ('{title}'): {e}")
            failed += 1

    logger.info(
        f"Backfill complete: {processed} processed, {failed} failed out of {total} total."
    )

    if failed > 0:
        logger.warning(f"{failed} jobs failed — check logs above and rerun for those IDs.")


def rescore_active_users() -> None:
    """
    After backfilling structured fields, trigger rescoring for all active users
    so their job_matches reflect the hybrid scoring formula against the new fields.
    """
    from app.services.scoring_service import scoring_service
    from app.repositories.uow import UnitOfWork
    from app.models.orm import ResumeORM

    logger.info("Refreshing scoring cache and rescoring all active users...")
    scoring_service.cache.refresh()

    with UnitOfWork() as uow:
        active_users = [
            row[0] for row in
            uow.session.query(ResumeORM.user_id).filter(ResumeORM.is_active == True).all()
        ]

    logger.info(f"Found {len(active_users)} active user(s) to rescore.")
    for user_id in active_users:
        try:
            logger.info(f"Rescoring jobs for user {user_id}...")
            scoring_service.score_all_jobs_for_user(user_id)
        except Exception as e:
            logger.error(f"Failed to rescore user {user_id}: {e}")

    logger.info("Rescoring complete.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Backfill structured job fields using job_parser.")
    parser.add_argument("--dry-run", action="store_true", help="Preview counts without writing to DB.")
    parser.add_argument("--limit", type=int, default=0, help="Max number of jobs to process (0 = all).")
    parser.add_argument("--force", action="store_true", help="Reprocess jobs already at current parser version.")
    parser.add_argument("--rescore", action="store_true", help="Trigger rescore for all active users after backfill.")
    args = parser.parse_args()

    run_backfill(dry_run=args.dry_run, limit=args.limit, force=args.force)

    if args.rescore and not args.dry_run:
        rescore_active_users()
