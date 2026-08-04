import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes.api import router as api_router
from app.routes.applications import router as applications_router
from app.routes.dashboard import router as dashboard_router
from app.routes.auth import router as auth_router
from app.routes.resumes import router as resumes_router
from app.routes.matches import router as matches_router
from app.routes.streaming import router as streaming_router
from app.routes.admin import router as admin_router
from app.config import settings
from app.services.llm_router_factory import get_llm_router

logger = logging.getLogger(__name__)

from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler
from app.rate_limiter import limiter

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.config import validate_jwt_secret
    validate_jwt_secret()

    try:
        from app.log_context import CorrelationIdFilter
        root_logger = logging.getLogger()
        from app.services.seeder import seed_if_empty
        seed_if_empty()

        if settings.run_workers_in_process:
            from app.services.ingestion.embedding_worker import embedding_worker
            from app.services.ingestion.scoring_worker import scoring_worker
            from app.services.job_scheduler import job_scheduler
            embedding_worker.start()
            scoring_worker.start()
            job_scheduler.start(run_immediately=True)
            logger.info("Background workers started in-process (development mode).")
        else:
            logger.info("In-process background workers disabled (RUN_WORKERS_IN_PROCESS=false). Expecting external worker process.")
    except Exception:
        logger.exception("Startup initialization failed")
        raise

    yield

    try:
        if settings.run_workers_in_process:
            from app.services.ingestion.embedding_worker import embedding_worker
            from app.services.ingestion.scoring_worker import scoring_worker
            from app.services.job_scheduler import job_scheduler
            job_scheduler.stop()
            scoring_worker.stop()
            embedding_worker.stop()
    except Exception:
        logger.exception("Shutdown cleanup failed")

app = FastAPI(title="JobLens API", version="0.1.0", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# --- CORS ---
# Origins are read from FRONTEND_URL (comma-separated for multi-origin support,
# e.g. "http://localhost:5173,https://joblens.example.com").
# allow_credentials is intentionally False: the API uses Bearer tokens, not
# cookies. Re-enable only if cookie-based auth is ever adopted.
_allowed_origins = [o.strip() for o in settings.frontend_url.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api")
app.include_router(api_router, prefix="/api")
app.include_router(resumes_router, prefix="/api")
app.include_router(matches_router, prefix="/api")
app.include_router(streaming_router, prefix="/api")
app.include_router(admin_router, prefix="/api")
app.include_router(applications_router, prefix="/api")
app.include_router(dashboard_router, prefix="/api")


@app.get("/health")
def health_check():
    from app.services.ingestion.queue import embedding_queue
    from app.services.job_scheduler import job_scheduler
    from app.services.ingestion.scoring_worker import scoring_worker
    from app.repositories.uow import UnitOfWork
    from sqlalchemy import text

    db_ok = False
    try:
        with UnitOfWork() as uow:
            uow.session.execute(text("SELECT 1"))
            db_ok = True
    except Exception as e:
        logger.error(f"Database health ping failed: {e}")

    redis_ok = False
    try:
        if hasattr(embedding_queue, "client") and embedding_queue.client is not None:
            embedding_queue.client.ping()
            redis_ok = True
    except Exception:
        pass

    cache = scoring_worker.scoring_service.cache
    cache_last_refreshed = getattr(cache, "_last_refreshed_at", None)

    _roles = ["rationale", "gap_analysis", "resume_parsing", "notification"]
    llm_status = {
        role: {
            "requested": get_llm_router(role).requested_provider,
            "active": get_llm_router(role).active_provider,
            "degraded": get_llm_router(role).requested_provider != get_llm_router(role).active_provider,
        }
        for role in _roles
    }

    return {
        "status": "ok" if db_ok else "degraded",
        "database_connected": db_ok,
        "queue_backend": embedding_queue.queue_backend,
        "redis_connected": redis_ok,
        "scheduler_last_run": (
            job_scheduler.last_run.isoformat() if job_scheduler.last_run else None
        ),
        "scheduler_status": job_scheduler.get_status()["status"],
        "resume_cache_size": len(cache.get_all()),
        "resume_cache_last_refreshed": (
            cache_last_refreshed.isoformat() if cache_last_refreshed else None
        ),
        "llm_providers": llm_status,
    }

