import time
import logging
from datetime import datetime, timezone

from typing import List, Dict, Any, Optional
from app.config import settings
from app.repositories.uow import UnitOfWork
from app.services.ingestion.source_registry import SourceRegistry
from app.services.ingestion.connectors import (
    GreenhouseConnector, LeverConnector, AshbyConnector,
    AdzunaConnector, RemotiveConnector, ArbeitnowConnector,
    JoobleConnector,
    ConnectorResultV1
)
from app.services.ingestion.normalizer import normalize_job
from app.services.ingestion.queue import embedding_queue
from app.nodes.normalize import normalize_text

logger = logging.getLogger("ingestion_pipeline")

# Source type sets — used to scope pipeline runs to a subset of connectors.
# AGGREGATOR_TYPES accept keyword/location queries; FIXED_BOARD_TYPES don't.
AGGREGATOR_TYPES: frozenset[str] = frozenset({"adzuna", "remotive", "arbeitnow", "jooble"})
FIXED_BOARD_TYPES: frozenset[str] = frozenset({"greenhouse", "lever", "ashby"})

def _extract_location_str(raw_item: Dict[str, Any]) -> str:
    loc_parts = []
    loc_val = raw_item.get("location")
    if isinstance(loc_val, dict):
        loc_parts.append(str(loc_val.get("name") or loc_val.get("display_name") or ""))
    elif isinstance(loc_val, str):
        loc_parts.append(loc_val)

    cats = raw_item.get("categories")
    if isinstance(cats, dict) and cats.get("location"):
        loc_parts.append(str(cats.get("location")))

    if raw_item.get("candidate_required_location"):
        loc_parts.append(str(raw_item.get("candidate_required_location")))

    if raw_item.get("address"):
        loc_parts.append(str(raw_item.get("address")))

    if raw_item.get("workplace_type"):
        loc_parts.append(str(raw_item.get("workplace_type")))

    if raw_item.get("remote") is True or raw_item.get("is_remote") is True:
        loc_parts.append("remote")

    return " ".join([p for p in loc_parts if p]).lower()


def run_ingestion_pipeline(
    keywords: Optional[List[str]] = None,
    location: Optional[str] = None,
    force: bool = False,
    source_types: Optional[frozenset[str]] = None,
) -> Dict[str, Any]:
    """
    Execute live ingestion across enabled sources in registry.

    Args:
        keywords:     Resume-derived search terms injected into aggregator queries.
        location:     Optional location filter.
        force:        Bypass per-source poll_interval_minutes cadence gate.
        source_types: Optional set of source type strings to restrict which
                      connectors run (e.g. AGGREGATOR_TYPES or FIXED_BOARD_TYPES).
                      None (default) runs all active sources — preserves existing
                      behavior for every call site that doesn’t opt in.

    Connectors fetch raw jobs -> Pipeline filters & normalizes -> Deterministic
    Deduplication -> Incremental PostgreSQL update -> Enqueue for embedding.
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
        "ashby": AshbyConnector(),
        "adzuna": AdzunaConnector(),
        "remotive": RemotiveConnector(),
        "arbeitnow": ArbeitnowConnector(),
        "jooble": JoobleConnector()
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

    for src in sources:
        source_type = src["source_type"].lower()

        # source_types scope filter: skip sources not in the requested set
        if source_types is not None and source_type not in source_types:
            continue

        if source_type == "greenhouse" and not getattr(settings, "greenhouse_enabled", True):
            continue
        if source_type == "lever" and not getattr(settings, "lever_enabled", True):
            continue
        if source_type == "ashby" and not getattr(settings, "ashby_enabled", True):
            continue
        if source_type in AGGREGATOR_TYPES and not getattr(settings, f"{source_type}_enabled", True):
            continue
        # Aggregator sources without any resume-derived keywords aren't worth
        # querying (they'd just return an unfiltered generic feed each run).
        if source_type in AGGREGATOR_TYPES and not keywords:
            logger.info(f"Skipping aggregator source '{src['name']}': no keywords supplied.")
            continue

        # Per-source cadence check: skip if polled too recently unless forced
        if not force and src.get("last_fetched_at"):
            last_fetched = src["last_fetched_at"]
            if isinstance(last_fetched, datetime):
                # Ensure naive vs aware datetime safety
                if last_fetched.tzinfo is None:
                    last_fetched = last_fetched.replace(tzinfo=timezone.utc)
                elapsed_min = (datetime.now(timezone.utc) - last_fetched).total_seconds() / 60.0

                poll_interval = src.get("poll_interval_minutes") or 60
                if elapsed_min < poll_interval:
                    logger.info(f"Skipping source '{src['name']}': fetched {elapsed_min:.1f}m ago (cadence {poll_interval}m).")
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
        fetch_config = src
        if source_type in AGGREGATOR_TYPES:
            fetch_config = {**src, "keywords": keywords, "location": location}
        res: ConnectorResultV1 = connector.fetch(fetch_config)

        # Scoped DB lookup for incoming raw URLs/IDs to avoid full table scan
        raw_urls = [str(raw.get("url")) for raw in res.raw_items if isinstance(raw, dict) and raw.get("url") is not None]
        raw_ids = [str(raw.get("id")) for raw in res.raw_items if isinstance(raw, dict) and raw.get("id") is not None]
        with UnitOfWork() as uow:
            if raw_urls:
                seen_urls.update(uow.jobs.get_existing_urls(raw_urls))
            if raw_ids:
                seen_ids.update(uow.jobs.get_existing_ids(raw_ids))



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

            # 2. Location filtering (OR matching across terms; no description search for 'remote' to avoid false positives)
            if location:
                terms = [t.strip().lower() for t in location.split(",") if t.strip()]
                raw_loc = _extract_location_str(raw_item)
                posting_title = posting.title.lower()

                matched = False
                for term in terms:
                    if term == "remote":
                        if "remote" in raw_loc or "remote" in posting_title or raw_item.get("remote") is True or raw_item.get("is_remote") is True:
                            matched = True
                            break
                    else:
                        if term in raw_loc or term in posting_title:
                            matched = True
                            break
                if not matched:
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
                completed_at=datetime.now(timezone.utc),
                jobs_fetched=res.jobs_fetched,
                jobs_inserted=inserted,
                jobs_updated=updated,
                duplicates_removed=duplicates,
                failures=failures,
                duration_ms=res.duration * 1000.0,
                status="Success" if failures == 0 else "Partial"
            )
            from app.models.orm import JobSourceORM
            js = uow.session.query(JobSourceORM).filter(JobSourceORM.name == src["name"]).first()
            if js:
                js.last_fetched_at = datetime.now(timezone.utc)
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
