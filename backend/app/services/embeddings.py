import logging
from typing import List, Union
import numpy as np
from sentence_transformers import SentenceTransformer
from app.services.interfaces import IEmbeddingService

logger = logging.getLogger(__name__)

class SentenceTransformerEmbeddingService(IEmbeddingService):
    _instance = None
    _model = None
    MODEL_NAME = "BAAI/bge-small-en-v1.5"
    JOB_PREFIX = "Represent this job posting for semantic retrieval: "
    RESUME_PREFIX = "Represent this resume for semantic retrieval: "

    def __init__(self, model_name: str = MODEL_NAME):
        if SentenceTransformerEmbeddingService._model is None:
            logger.info(f"Loading SentenceTransformer model: {model_name}")
            SentenceTransformerEmbeddingService._model = SentenceTransformer(model_name)
            logger.info("Model loaded successfully.")
        self.model = SentenceTransformerEmbeddingService._model

    def embed_text(self, text: str, prefix: str = "") -> Union[List[float], np.ndarray]:
        full_text = f"{prefix}{text}" if prefix else text
        embedding = self.model.encode(full_text, normalize_embeddings=True)
        return embedding

    def embed_texts(self, texts: List[str], prefix: str = "") -> Union[List[List[float]], np.ndarray]:
        full_texts = [f"{prefix}{t}" if prefix else t for t in texts]
        embeddings = self.model.encode(full_texts, normalize_embeddings=True)
        return embeddings

    def embed_job(self, text: str) -> np.ndarray:
        return self.embed_text(text, prefix=self.JOB_PREFIX)

    def embed_jobs(self, texts: List[str]) -> np.ndarray:
        return self.embed_texts(texts, prefix=self.JOB_PREFIX)

    def embed_resume_section(self, text: str) -> np.ndarray:
        return self.embed_text(text, prefix=self.RESUME_PREFIX)

    def embed_resume_sections(self, texts: List[str]) -> np.ndarray:
        return self.embed_texts(texts, prefix=self.RESUME_PREFIX)

# Create a default singleton instance for easy import if needed
embedding_service = SentenceTransformerEmbeddingService()
