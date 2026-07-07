import time
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from app.config import settings
from app.repositories.uow import UnitOfWork
from app.services.ingestion.source_registry import SourceRegistry
from app.services.ingestion.connectors import GreenhouseConnector, LeverConnector, AshbyConnector, ConnectorResultV1
from app.services.ingestion.normalizer import normalize_job
from app.services.ingestion.queue import embedding_queue
from app.nodes.normalize import normalize_text

logger = logging.getLogger("ingestion_pipeline")

def run_ingestion_pipeline(keywords: Optional[List[str]] = None, location: Optional[str] = None) -> Dict[str, Any]:
    """
    Execute live ingestion across enabled sources in registry.
    Connectors fetch raw jobs -> Pipeline filters & normalizes -> Deterministic Deduplication -> Incremental PostgreSQL update -> Enqueue for embedding.
    """
    start_time = time.time()
    logger.info("=== Starting Live Job Ingestion Pipeline ===")
    sources = SourceRegistry.get_active_sources()
    if not sources:
        logger.warning("No active sources found in SourceRegistry. Please check job_sources table.")
        return {"status": "empty", "duration_s": 0.0, "sources_processed": 0}

    connectors_map = {
        "greenhouse": GreenhouseConnector(),
        "lever": LeverConnector(),
        "ashby": AshbyConnector()
    }

    # Global deduplication trackers across all sources in this run
    seen_urls = set()
    seen_ids = set()
    seen_titles_companies = set()

    total_fetched = 0
    total_inserted = 0
    total_updated = 0
    total_duplicates = 0
    total_failures = 0
    sources_processed = 0

    with UnitOfWork() as uow:
        # Pre-populate seen sets with existing DB jobs to prevent duplicates across runs
        existing_jobs = uow.jobs.get_all_postings()
        for ej in existing_jobs:
            if ej.url:
                seen_urls.add(ej.url)
            if ej.id:
                seen_ids.add(ej.id)
            seen_titles_companies.add((normalize_text(ej.company), normalize_text(ej.title)))

    for src in sources:
        source_type = src["source_type"].lower()
        if source_type == "greenhouse" and not getattr(settings, "greenhouse_enabled", True):
            continue
        if source_type == "lever" and not getattr(settings, "lever_enabled", True):
            continue
        if source_type == "ashby" and not getattr(settings, "ashby_enabled", True):
            continue

        connector = connectors_map.get(source_type)
        if not connector:
            logger.warning(f"No connector implemented for source type '{source_type}'. Skipping.")
            continue

        sources_processed += 1
        with UnitOfWork() as uow:
            run_rec = uow.ingestion_runs.create(source=src["name"], status="Running")
            uow.commit()
            run_id = run_rec["id"]

        logger.info(f"Executing connector for {src['name']}...")
        res: ConnectorResultV1 = connector.fetch(src)

        inserted = 0
        updated = 0
        duplicates = 0
        failures = res.failures

        for raw_item in res.raw_items:
            posting = normalize_job(raw_item, src["source_type"], src["board"])
            if not posting:
                failures += 1
                continue

            # 1. Keyword filtering
            if keywords:
                text_to_search = f"{posting.title} {posting.description}".lower()
                if not any(kw.lower() in text_to_search for kw in keywords):
                    continue

            # 2. Location filtering
            if location:
                loc_lower = location.lower()
                raw_loc = str(raw_item.get("location", "") or raw_item.get("categories", {}).get("location", "") or raw_item.get("address", "")).lower()
                if loc_lower not in raw_loc and loc_lower not in posting.title.lower() and loc_lower != "remote":
                    continue

            # 3. Deterministic Deduplication
            norm_title = normalize_text(posting.title)
            norm_comp = normalize_text(posting.company)
            key_tc = (norm_comp, norm_title)

            if posting.url in seen_urls or posting.id in seen_ids or key_tc in seen_titles_companies:
                duplicates += 1
                logger.info(f"Duplicate removed: '{posting.title}' at '{posting.company}'")
                continue

            seen_urls.add(posting.url)
            seen_ids.add(posting.id)
            seen_titles_companies.add(key_tc)

            # 4. Incremental PostgreSQL update
            with UnitOfWork() as uow:
                existing = uow.jobs.get_by_id_or_url(posting.url)
                if not existing:
                    existing = uow.jobs.get_by_id_or_url(posting.id)

                if not existing:
                    # New job -> store immediately without embedding, queue for worker
                    uow.jobs.upsert(
                        title=posting.title,
                        company_name=posting.company,
                        description=posting.description,
                        url=posting.url,
                        source=posting.source,
                        job_id=posting.id
                    )
                    uow.commit()
                    embedding_queue.enqueue(posting.id)
                    inserted += 1
                else:
                    # Existing job -> check if description or title changed
                    if existing.description != posting.description or existing.title != posting.title:
                        uow.jobs.upsert(
                            title=posting.title,
                            company_name=posting.company,
                            description=posting.description,
                            url=posting.url,
                            source=posting.source,
                            job_id=posting.id
                        )
                        uow.commit()
                        if existing.description != posting.description:
                            embedding_queue.enqueue(posting.id)
                        updated += 1
                    else:
                        # Unchanged job -> ignore
                        pass

        with UnitOfWork() as uow:
            uow.ingestion_runs.update(
                run_id=run_id,
                completed_at=datetime.utcnow(),
                jobs_fetched=res.jobs_fetched,
                jobs_inserted=inserted,
                jobs_updated=updated,
                duplicates_removed=duplicates,
                failures=failures,
                duration_ms=res.duration * 1000.0,
                status="Success" if failures == 0 else "Partial"
            )
            uow.commit()

        total_fetched += res.jobs_fetched
        total_inserted += inserted
        total_updated += updated
        total_duplicates += duplicates
        total_failures += failures

        logger.info(f"\n--- Ingestion Stats for {src['name']} ---")
        logger.info(f"Fetched: {res.jobs_fetched}")
        logger.info(f"Inserted: {inserted}")
        logger.info(f"Updated: {updated}")
        logger.info(f"Duplicates: {duplicates}")
        logger.info(f"Failures: {failures}\n")

    total_duration = time.time() - start_time
    logger.info(f"=== Ingestion Pipeline Completed in {total_duration:.2f}s ===")
    logger.info(f"Total -> Fetched: {total_fetched} | Inserted: {total_inserted} | Updated: {total_updated} | Duplicates: {total_duplicates} | Failures: {total_failures}")

    return {
        "status": "completed",
        "duration_s": total_duration,
        "sources_processed": sources_processed,
        "total_fetched": total_fetched,
        "total_inserted": total_inserted,
        "total_updated": total_updated,
        "total_duplicates": total_duplicates,
        "total_failures": total_failures
    }
