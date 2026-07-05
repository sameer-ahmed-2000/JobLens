import os
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseModel):
    app_name: str = "JobLens MVP"
    ollama_base_url: str = os.getenv("LLAMA_API_BASE", os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"))
    model_name: str = os.getenv("LLAMA_MODEL", os.getenv("MODEL_NAME", "llama3"))
    top_n_rationales: int = int(os.getenv("TOP_N_RATIONALES", "10"))
    database_url: str = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/joblens")

settings = Settings()
