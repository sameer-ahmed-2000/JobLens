import os
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseModel):
    app_name: str = "JobLens MVP"

    # LLM Provider selection: "ollama" | "freemodel" | "openai"
    llm_provider: str = os.getenv("LLM_PROVIDER", "ollama")

    # Ollama
    ollama_base_url: str = os.getenv("LLAMA_API_BASE", os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"))
    model_name: str = os.getenv("LLAMA_MODEL", os.getenv("MODEL_NAME", "llama3"))

    # FreeModel.dev (OpenAI-compatible)
    freemodel_api_key: str = os.getenv("FREEMODEL_API_KEY", "")
    freemodel_base_url: str = os.getenv("FREEMODEL_BASE_URL", "https://api.freemodel.dev/v1")
    freemodel_model: str = os.getenv("FREEMODEL_MODEL", "auto")

    # OpenAI (optional future provider)
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    top_n_rationales: int = int(os.getenv("TOP_N_RATIONALES", "10"))
    database_url: str = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/joblens")

    # Real-time, resume-driven aggregator sources
    adzuna_app_id: str = os.getenv("ADZUNA_APP_ID", "")
    adzuna_app_key: str = os.getenv("ADZUNA_APP_KEY", "")
    adzuna_country: str = os.getenv("ADZUNA_COUNTRY", "in")  # ISO country code, e.g. "in", "us", "gb"
    default_location: str = os.getenv("DEFAULT_JOB_LOCATION", "")  # e.g. "Chennai" or "" for no filter

    adzuna_enabled: bool = os.getenv("ADZUNA_ENABLED", "true").lower() == "true"
    remotive_enabled: bool = os.getenv("REMOTIVE_ENABLED", "true").lower() == "true"
    arbeitnow_enabled: bool = os.getenv("ARBEITNOW_ENABLED", "true").lower() == "true"

    # Minimum minutes between resume-driven live searches, to avoid hammering
    # free-tier aggregator APIs on every /discover call.
    live_search_min_interval_minutes: int = int(os.getenv("LIVE_SEARCH_MIN_INTERVAL_MINUTES", "15"))

settings = Settings()
