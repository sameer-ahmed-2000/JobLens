import os
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

_raw_db_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/joblens")
if _raw_db_url.startswith("postgres://"):
    _raw_db_url = _raw_db_url.replace("postgres://", "postgresql://", 1)

class Settings(BaseModel):
    app_name: str = "JobLens MVP"
    environment: str = os.getenv("ENVIRONMENT", "development").lower()

    # LLM Provider selection

    # Legacy single-provider var — kept as the default when role-specific vars are unset.
    # Set LLM_PROVIDER_DEFAULT (or the old LLM_PROVIDER) to choose the global fallback.
    llm_provider_default: str = os.getenv(
        "LLM_PROVIDER_DEFAULT",
        os.getenv("LLM_PROVIDER", "ollama")  # legacy fallback so old .env files keep working
    )

    # Per-role provider overrides (empty string = use llm_provider_default)
    llm_provider_rationale: str = os.getenv("LLM_PROVIDER_RATIONALE", "")
    llm_provider_gap_analysis: str = os.getenv("LLM_PROVIDER_GAP_ANALYSIS", "")
    llm_provider_resume_parsing: str = os.getenv("LLM_PROVIDER_RESUME_PARSING", "")
    llm_provider_notification: str = os.getenv("LLM_PROVIDER_NOTIFICATION", "")

    # Ollama
    ollama_base_url: str = os.getenv("LLAMA_API_BASE", os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"))
    model_name: str = os.getenv("LLAMA_MODEL", os.getenv("MODEL_NAME", "llama3"))

    # FreeModel.dev (OpenAI-compatible)
    freemodel_api_key: str = os.getenv("FREEMODEL_API_KEY", "")
    freemodel_base_url: str = os.getenv("FREEMODEL_BASE_URL", "https://api.freemodel.dev/v1")
    freemodel_model: str = os.getenv("FREEMODEL_MODEL", "auto")

    # OpenAI
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    # Groq (OpenAI-compatible, fast/cheap inference)
    groq_api_key: str = os.getenv("GROQ_API_KEY", "")
    groq_model: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

    # Gemini (Google — structured JSON extraction)
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    gemini_model: str = os.getenv("GEMINI_MODEL", "")

    top_n_rationales: int = int(os.getenv("TOP_N_RATIONALES", "10"))
    job_stale_after_days: int = int(os.getenv("JOB_STALE_AFTER_DAYS", "14"))
    database_url: str = _raw_db_url

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
    # If REDIS_URL is set, it will be used directly. Otherwise, the URL is built
    # from host, port, password, and db components.
    redis_url: str = os.getenv("REDIS_URL", "")
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

    # JWT Authentication Settings
    jwt_secret_key: str = os.getenv("JWT_SECRET_KEY", "super-secret-key-change-me")
    jwt_algorithm: str = os.getenv("JWT_ALGORITHM", "HS256")
    jwt_expiration_minutes: int = int(os.getenv("JWT_EXPIRATION_MINUTES", "43200"))  # Default to 30 days

    # Cloudinary and Resume upload settings
    cloudinary_cloud_name: str = os.getenv("CLOUDINARY_CLOUD_NAME", "")
    cloudinary_api_key: str = os.getenv("CLOUDINARY_API_KEY", "")
    cloudinary_api_secret: str = os.getenv("CLOUDINARY_API_SECRET", "")
    resume_max_size_mb: int = int(os.getenv("RESUME_MAX_SIZE_MB", "5"))
    resume_processing_max_retries: int = int(os.getenv("RESUME_PROCESSING_MAX_RETRIES", "3"))

# Build redis_url after Settings is instantiated.
# Must be done at module level (not inside __init__) so that load_dotenv()
# has already been called and os.getenv() returns the real values.
_ru = os.getenv("REDIS_URL", "")
_rp = os.getenv("REDIS_PASSWORD", "")
_rh = os.getenv("REDIS_HOST", "localhost")
_rport = os.getenv("REDIS_PORT", "6379")
_rdb = os.getenv("REDIS_DB", "0")

settings = Settings()
# Override redis_url with the provided REDIS_URL or programmatic URL so the
# credentials are always embedded correctly regardless of .env contents.
if not _ru:
    _ru = f"redis://:{_rp}@{_rh}:{_rport}/{_rdb}" if _rp else f"redis://{_rh}:{_rport}/{_rdb}"

object.__setattr__(
    settings,
    "redis_url",
    _ru
)


def validate_jwt_secret(settings_obj=None):
    """
    Validates JWT_SECRET_KEY security.
    Evaluates dynamically from environment variables at execution time to support runtime environment changes.
    Raises RuntimeError if insecure in non-development environments; logs a warning in development mode.
    """
    target = settings_obj or settings
    env = os.getenv("ENVIRONMENT", target.environment).lower()
    secret = os.getenv("JWT_SECRET_KEY", target.jwt_secret_key)
    
    if secret == "super-secret-key-change-me":
        if env != "development":
            raise RuntimeError(
                "CRITICAL SECURITY FAILURE: JWT_SECRET_KEY is set to default insecure key "
                f"('super-secret-key-change-me') in non-development environment '{env}'! Refusing to start."
            )
        import logging
        logging.getLogger("app.config").warning(
            "SECURITY WARNING: JWT_SECRET_KEY is set to default insecure key ('super-secret-key-change-me'). "
            "Set a strong JWT_SECRET_KEY before deploying to production!"
        )

