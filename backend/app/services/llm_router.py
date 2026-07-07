import json
import logging
from typing import Any, Optional
from app.services.interfaces import ILLMRouter
from app.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Backend: Ollama
# ---------------------------------------------------------------------------
class OllamaBackend:
    def __init__(self):
        import httpx
        self._httpx = httpx
        self.base_url = settings.ollama_base_url.rstrip("/")
        self.model_name = settings.model_name
        self._is_available: Optional[bool] = None

    def health_check(self, timeout: float = 2.0) -> bool:
        try:
            with self._httpx.Client(timeout=timeout) as client:
                resp = client.get(f"{self.base_url}/api/tags")
                if resp.status_code == 200:
                    self._is_available = True
                    return True
        except Exception as e:
            logger.warning(f"Ollama health check failed: {e}")
        self._is_available = False
        return False

    def generate(self, prompt: str, system_prompt: str = "", timeout: float = 10.0) -> str:
        if self._is_available is False:
            if not self.health_check(timeout=1.0):
                logger.info("Ollama offline; degrading gracefully.")
                return "Rationale unavailable."

        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
            "options": {"num_predict": 60, "temperature": 0.3}
        }
        if system_prompt:
            payload["system"] = system_prompt

        try:
            with self._httpx.Client(timeout=timeout) as client:
                resp = client.post(f"{self.base_url}/api/generate", json=payload)
                if resp.status_code == 200:
                    text = resp.json().get("response", "").strip()
                    return text or "Rationale unavailable."
                logger.warning(f"Ollama HTTP {resp.status_code}: {resp.text[:100]}")
        except Exception as e:
            logger.warning(f"Ollama generation request failed gracefully: {e}")
            self._is_available = False
        return "Rationale unavailable."

    def generate_json(self, prompt: str, timeout: float = 10.0) -> Any:
        if not self.health_check(timeout=1.0):
            return None
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "format": "json",
            "stream": False,
            "options": {"temperature": 0.1}
        }
        try:
            with self._httpx.Client(timeout=timeout) as client:
                resp = client.post(f"{self.base_url}/api/generate", json=payload)
                if resp.status_code == 200:
                    return json.loads(resp.json().get("response", "{}"))
        except Exception as e:
            logger.warning(f"Ollama JSON generation failed: {e}")
        return None


# ---------------------------------------------------------------------------
# Backend: FreeModel.dev / OpenAI-compatible
# ---------------------------------------------------------------------------
class OpenAICompatibleBackend:
    """Shared backend for any OpenAI-compatible API (FreeModel.dev, OpenAI, etc.)."""

    def __init__(self, base_url: str, api_key: str, model: str, provider_name: str):
        self.base_url = base_url
        self.api_key = api_key
        self.model = model
        self.provider_name = provider_name

    def _get_client(self):
        try:
            from openai import OpenAI
            return OpenAI(base_url=self.base_url, api_key=self.api_key)
        except ImportError:
            raise RuntimeError(
                "openai package not installed. Run: pip install openai"
            )

    def generate(self, prompt: str, system_prompt: str = "", timeout: float = 30.0) -> str:
        try:
            client = self._get_client()
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            response = client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=200,
                temperature=0.3,
                timeout=timeout
            )
            text = response.choices[0].message.content or ""
            return text.strip() or "Rationale unavailable."
        except Exception as e:
            logger.warning(f"{self.provider_name} generation failed gracefully: {e}")
            return "Rationale unavailable."

    def generate_json(self, prompt: str, timeout: float = 30.0) -> Any:
        try:
            client = self._get_client()
            messages = [
                {"role": "system", "content": "You are a structured JSON extractor. Always respond with valid JSON only."},
                {"role": "user", "content": prompt}
            ]
            response = client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=500,
                temperature=0.1,
                timeout=timeout,
                response_format={"type": "json_object"}
            )
            raw = response.choices[0].message.content or "{}"
            return json.loads(raw)
        except json.JSONDecodeError as e:
            logger.warning(f"{self.provider_name} JSON parse error: {e}")
        except Exception as e:
            logger.warning(f"{self.provider_name} JSON generation failed gracefully: {e}")
        return None


# ---------------------------------------------------------------------------
# Unified LLMRouter — provider-agnostic
# ---------------------------------------------------------------------------
class LLMRouter(ILLMRouter):
    """
    Provider-agnostic LLM router. Switch backends via LLM_PROVIDER env var:
      - "ollama"     (default, local)
      - "freemodel"  (FreeModel.dev, OpenAI-compatible)
      - "openai"     (OpenAI API)
    """

    def __init__(self):
        provider = settings.llm_provider.lower().strip()
        logger.info(f"LLMRouter initializing with provider: '{provider}'")

        if provider == "freemodel":
            if not settings.freemodel_api_key:
                logger.warning("FREEMODEL_API_KEY not set. Falling back to Ollama.")
                self._backend = OllamaBackend()
            else:
                self._backend = OpenAICompatibleBackend(
                    base_url=settings.freemodel_base_url,
                    api_key=settings.freemodel_api_key,
                    model=settings.freemodel_model,
                    provider_name="FreeModel.dev"
                )

        elif provider == "openai":
            if not settings.openai_api_key:
                logger.warning("OPENAI_API_KEY not set. Falling back to Ollama.")
                self._backend = OllamaBackend()
            else:
                self._backend = OpenAICompatibleBackend(
                    base_url="https://api.openai.com/v1",
                    api_key=settings.openai_api_key,
                    model=settings.openai_model,
                    provider_name="OpenAI"
                )

        else:
            if provider != "ollama":
                logger.warning(f"Unknown LLM_PROVIDER '{provider}'. Defaulting to Ollama.")
            self._backend = OllamaBackend()

        logger.info(f"LLMRouter ready: {type(self._backend).__name__}")

    def generate(self, prompt: str, system_prompt: str = "", timeout: float = 10.0) -> str:
        return self._backend.generate(prompt=prompt, system_prompt=system_prompt, timeout=timeout)

    def generate_json(self, prompt: str, timeout: float = 10.0) -> Any:
        return self._backend.generate_json(prompt=prompt, timeout=timeout)

    # ILLMRouter interface
    def generate_completion(self, prompt: str, system_prompt: str = "") -> str:
        return self.generate(prompt=prompt, system_prompt=system_prompt)

    def generate_structured_output(self, prompt: str, schema: Any, system_prompt: str = "") -> Any:
        return self.generate_json(prompt=prompt)


# Singleton instance — all nodes import this
llm_router = LLMRouter()
