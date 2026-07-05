from abc import ABC, abstractmethod
from typing import List, Dict, Any

class IEmbeddingService(ABC):
    @abstractmethod
    def embed_text(self, text: str) -> List[float]:
        """Convert a single string into a vector embedding."""
        pass

    @abstractmethod
    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Convert multiple strings into vector embeddings."""
        pass

class ILLMRouter(ABC):
    @abstractmethod
    def generate_completion(self, prompt: str, system_prompt: str = "") -> str:
        """Generate a text completion using the configured LLM."""
        pass
        
    @abstractmethod
    def generate_structured_output(self, prompt: str, schema: Any, system_prompt: str = "") -> Any:
        """Generate a structured output matching the provided Pydantic schema."""
        pass

class IResumeIndex(ABC):
    @abstractmethod
    def add_resume(self, resume_id: str, skills: List[str], experience: str) -> bool:
        """Index a resume into the vector store."""
        pass

    @abstractmethod
    def search_skills(self, required_skills: List[str], top_k: int = 5) -> List[Dict[str, Any]]:
        """Search for matches against required skills."""
        pass
