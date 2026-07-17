from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes.api import router as api_router
from app.routes.applications import router as applications_router
from app.routes.dashboard import router as dashboard_router

app = FastAPI(title="JobLens API", version="0.1.0")

# Allow frontend to access the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # For MVP, allow all. Update for production.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.services.seeder import seed_if_empty

app.include_router(api_router, prefix="/api")
app.include_router(applications_router, prefix="/api")
app.include_router(dashboard_router, prefix="/api")

@app.on_event("startup")
async def startup_event():
    try:
        seed_if_empty()
        from app.services.ingestion.embedding_worker import embedding_worker
        from app.services.ingestion.scoring_worker import scoring_worker
        from app.services.job_scheduler import job_scheduler
        embedding_worker.start()
        scoring_worker.start()
        job_scheduler.start(run_immediately=True)
    except Exception as e:
        print(f"Startup initialization skipped or failed: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    try:
        from app.services.ingestion.embedding_worker import embedding_worker
        from app.services.ingestion.scoring_worker import scoring_worker
        from app.services.job_scheduler import job_scheduler
        job_scheduler.stop()
        scoring_worker.stop()
        embedding_worker.stop()
    except Exception as e:
        print(f"Shutdown cleanup failed: {e}")

@app.get("/health")
def health_check():
    from app.services.ingestion.queue import embedding_queue
    return {
        "status": "ok",
        "queue_backend": embedding_queue.queue_backend
    }

