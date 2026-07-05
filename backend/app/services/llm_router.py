import json
import logging
from typing import Any, Optional
import httpx
from app.services.interfaces import ILLMRouter
from app.config import settings

logger = logging.getLogger(__name__)

class OllamaLLMRouter(ILLMRouter):
    def __init__(self, base_url: Optional[str] = None, model_name: Optional[str] = None):
        self.base_url = (base_url or settings.ollama_base_url).rstrip("/")
        self.model_name = model_name or settings.model_name
        self._is_available: Optional[bool] = None

    def health_check(self, timeout: float = 2.0) -> bool:
        """Check if Ollama server is running and accessible."""
        try:
            url = f"{self.base_url}/api/tags"
            with httpx.Client(timeout=timeout) as client:
                response = client.get(url)
                if response.status_code == 200:
                    logger.debug("Ollama health check passed.")
                    self._is_available = True
                    return True
        except Exception as e:
            logger.warning(f"Ollama health check failed ({self.base_url}): {e}")
        self._is_available = False
        return False

    def generate(self, prompt: str, system_prompt: str = "", timeout: float = 10.0) -> str:
        """Generate text completion using Ollama with graceful degradation."""
        if self._is_available is False:
            # Try a quick re-check just in case it came online
            if not self.health_check(timeout=1.0):
                logger.info("Ollama is offline; degrading gracefully without throwing exception.")
                return "Rationale unavailable."

        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_predict": 60,
                "temperature": 0.3
            }
        }
        if system_prompt:
            payload["system"] = system_prompt

        try:
            with httpx.Client(timeout=timeout) as client:
                response = client.post(url, json=payload)
                if response.status_code == 200:
                    data = response.json()
                    res_text = data.get("response", "").strip()
                    return res_text if res_text else "Rationale unavailable."
                else:
                    logger.warning(f"Ollama returned HTTP {response.status_code}: {response.text}")
        except Exception as e:
            logger.warning(f"Ollama generation request failed gracefully: {e}")
            self._is_available = False

        return "Rationale unavailable."

    def generate_json(self, prompt: str, schema: Any = None, timeout: float = 10.0) -> Any:
        """Generate structured JSON output using Ollama."""
        if not self.health_check(timeout=1.0):
            return None

        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "format": "json",
            "stream": False,
            "options": {"temperature": 0.1}
        }

        try:
            with httpx.Client(timeout=timeout) as client:
                response = client.post(url, json=payload)
                if response.status_code == 200:
                    data = response.json()
                    raw_json = data.get("response", "{}")
                    parsed = json.loads(raw_json)
                    return parsed
        except Exception as e:
            logger.warning(f"Ollama JSON generation failed: {e}")

        return None

    # ILLMRouter interface implementations
    def generate_completion(self, prompt: str, system_prompt: str = "") -> str:
        return self.generate(prompt=prompt, system_prompt=system_prompt)
        
    def generate_structured_output(self, prompt: str, schema: Any, system_prompt: str = "") -> Any:
        return self.generate_json(prompt=prompt, schema=schema)

# Singleton instance
llm_router = OllamaLLMRouter()
