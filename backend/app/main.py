from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes.api import router as api_router

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

@app.on_event("startup")
async def startup_event():
    try:
        seed_if_empty()
    except Exception as e:
        print(f"Startup seeding check skipped or failed: {e}")

@app.get("/health")
def health_check():
    return {"status": "ok"}
