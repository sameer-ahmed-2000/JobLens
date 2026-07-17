import os
import json
import logging
import hashlib
from app.repositories.uow import UnitOfWork
from app.models.orm import JobSourceORM, UserORM

logger = logging.getLogger("seeder")

def seed_if_empty(uow_factory=UnitOfWork, force_reseed: bool = False) -> None:
    """
    Idempotently seeds PostgreSQL database from initial data files (resume.json, postings.json).
    Safe to run on every startup; checks existence and updates duplicates without failing.
    """
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    resume_path = os.path.join(base_dir, "data", "resume.json")
    postings_path = os.path.join(base_dir, "data", "postings.json")
    sources_path = os.path.join(base_dir, "data", "job_sources.json")

    if not os.path.exists(resume_path) or not os.path.exists(postings_path):
        logger.warning("Seed data files missing. Skipping database seed.")
        return

    logger.info("Running idempotent database seeding...")
    try:
        with uow_factory() as uow:
            # 1. Seed default user
            user = uow.users.get_by_email("user@joblens.ai")
            raw_token = "default-user-token"
            token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
            if not user:
                user = uow.users.create(
                    name="Demo User",
                    email="user@joblens.ai",
                    user_id="default-user-id",
                    token_hash=token_hash
                )
                logger.info(f"Created default user with API token: {raw_token}")
            else:
                if not user.get("token_hash"):
                    user_orm = uow.session.query(UserORM).filter(UserORM.id == user["id"]).first()
                    if user_orm:
                        user_orm.token_hash = token_hash
                        logger.info("Updated existing default user with API token hash.")

            # 2. Seed resume
            with open(resume_path, "r", encoding="utf-8") as f:
                res_data = json.load(f)
            
            uow.resumes.upsert_resume(
                user_id=user["id"],
                title=res_data.get("title", "AI Engineer"),
                years_experience=res_data.get("years_experience", 0.0),
                skills=res_data.get("skills", []),
                projects=res_data.get("projects", []),
                resume_id="default-resume-id"
            )
            logger.info("Idempotently seeded resume profile.")

            # 3. Seed companies and job postings
            with open(postings_path, "r", encoding="utf-8") as f:
                postings_data = json.load(f)

            count = 0
            for item in postings_data:
                comp_name = item.get("company", "Unknown Company")
                comp = uow.companies.lookup_or_create(name=comp_name)
                
                uow.jobs.upsert(
                    title=item.get("title", ""),
                    company_name=comp_name,
                    description=item.get("description", ""),
                    url=item.get("url", f"https://example.com/jobs/{item.get('id', count)}"),
                    source=item.get("source", "Seed"),
                    job_id=item.get("id"),
                    company_id=comp["id"]
                )
                count += 1

            # 4. Seed job sources; add any new ones from the file without touching
            # existing rows, so upgrading job_sources.json (e.g. adding new
            # aggregator sources) takes effect even on an already-seeded DB.
            if os.path.exists(sources_path):
                with open(sources_path, "r", encoding="utf-8") as f:
                    sources_data = json.load(f)

                existing_names = {
                    row[0] for row in uow.session.query(JobSourceORM.name).all()
                }
                added = 0
                for src in sources_data:
                    name = src.get("name", "")
                    if name and name not in existing_names:
                        src_obj = JobSourceORM(
                            name=name,
                            url=src.get("url", ""),
                            is_active=src.get("is_active", True)
                        )
                        uow.session.add(src_obj)
                        added += 1
                if added:
                    logger.info(f"Seeded {added} new job source(s) into JobSourceORM.")

            uow.commit()
            logger.info(f"Successfully seeded/updated {count} job postings in PostgreSQL.")
    except Exception as e:
        logger.error(f"Error during database seeding: {e}", exc_info=True)
        # We don't re-raise to avoid crashing app boot if database tables haven't been migrated yet
