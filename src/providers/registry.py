from src.config import get_ollama_settings, get_openai_settings
from src.providers.ollama_provider import OllamaProvider
from src.providers.openai_provider import OpenAIProvider


def build_provider_registry() -> dict[str, dict[str, object]]:
    ollama_settings = get_ollama_settings()
    registry: dict[str, dict[str, object]] = {
        "ollama": {
            "label": "Ollama (local)",
            "detail": f"Base URL: `{ollama_settings.base_url}`",
            "instance": OllamaProvider(ollama_settings),
        }
    }

    openai_settings = get_openai_settings()
    if openai_settings.api_key:
        registry["openai"] = {
            "label": "OpenAI",
            "detail": "Provider cloud opcional configurado por variável de ambiente",
            "instance": OpenAIProvider(openai_settings),
        }

    return registry