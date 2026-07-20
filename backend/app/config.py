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

    # Jooble aggregator (free tier: https://jooble.org/api/about)
    jooble_api_key: str = os.getenv("JOOBLE_API_KEY", "")
    jooble_enabled: bool = os.getenv("JOOBLE_ENABLED", "true").lower() == "true"
    default_location: str = os.getenv("DEFAULT_JOB_LOCATION", "")  # e.g. "Chennai" or "" for no filter

    adzuna_enabled: bool = os.getenv("ADZUNA_ENABLED", "true").lower() == "true"
    remotive_enabled: bool = os.getenv("REMOTIVE_ENABLED", "true").lower() == "true"
    arbeitnow_enabled: bool = os.getenv("ARBEITNOW_ENABLED", "true").lower() == "true"

    # Minimum minutes between resume-driven live searches, to avoid hammering
    # free-tier aggregator APIs on every /discover call.
    live_search_min_interval_minutes: int = int(os.getenv("LIVE_SEARCH_MIN_INTERVAL_MINUTES", "15"))

    # Redis configuration
    # URL is built from components to avoid python-dotenv's unreliable ${VAR}
    # interpolation within .env files. Set REDIS_PASSWORD, REDIS_HOST, etc.
    # individually — never set REDIS_URL directly.
    redis_password: str = os.getenv("REDIS_PASSWORD", "")
    redis_host: str = os.getenv("REDIS_HOST", "localhost")
    redis_port: int = int(os.getenv("REDIS_PORT", "6379"))
    redis_db: int = int(os.getenv("REDIS_DB", "0"))
    embedding_stream_maxlen: int = int(os.getenv("EMBEDDING_STREAM_MAXLEN", "10000"))
    embedding_max_retries: int = int(os.getenv("EMBEDDING_MAX_RETRIES", "3"))

    # SMTP Configuration
    smtp_host: str = os.getenv("SMTP_HOST", "localhost")
    smtp_port: int = int(os.getenv("SMTP_PORT", "1025"))
    smtp_username: str = os.getenv("SMTP_USERNAME", "")
    smtp_password: str = os.getenv("SMTP_PASSWORD", "")
    smtp_from: str = os.getenv("SMTP_FROM", "noreply@joblens.ai")

    # WhatsApp Configuration
    whatsapp_api_token: str = os.getenv("WHATSAPP_API_TOKEN", "")
    whatsapp_phone_number_id: str = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")

    # Notification settings
    max_notifs_per_hour: int = int(os.getenv("MAX_NOTIFS_PER_HOUR", "5"))
    frontend_url: str = os.getenv("FRONTEND_URL", "http://localhost:5173")

    # Self-Serve Onboarding Invite Protection
    signup_invite_token: str = os.getenv("SIGNUP_INVITE_TOKEN", "joblens-beta-2026")

# Build redis_url from components after Settings is instantiated.
# Must be done at module level (not inside __init__) so that load_dotenv()
# has already been called and os.getenv() returns the real values.
_rp = os.getenv("REDIS_PASSWORD", "")
_rh = os.getenv("REDIS_HOST", "localhost")
_rport = os.getenv("REDIS_PORT", "6379")
_rdb = os.getenv("REDIS_DB", "0")

settings = Settings()
# Override redis_url with the programmatically constructed URL so the
# auth credentials are always embedded correctly regardless of .env contents.
object.__setattr__(
    settings,
    "redis_url",
    f"redis://:{_rp}@{_rh}:{_rport}/{_rdb}" if _rp else f"redis://{_rh}:{_rport}/{_rdb}"
)
