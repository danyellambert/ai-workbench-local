import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


@dataclass(frozen=True)
class OllamaSettings:
    project_name: str
    base_url: str
    default_model: str
    default_temperature: float
    available_models_env: list[str]
    history_path: Path


@dataclass(frozen=True)
class OpenAISettings:
    api_key: str | None
    model: str


def get_ollama_settings() -> OllamaSettings:
    default_model = os.getenv("OLLAMA_MODEL", "qwen2.5-coder:7b")
    available_models_env = [
        model.strip()
        for model in os.getenv("OLLAMA_AVAILABLE_MODELS", "").split(",")
        if model.strip()
    ]

    return OllamaSettings(
        project_name=os.getenv("PROJECT_NAME", "AI Workbench Local"),
        base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1"),
        default_model=default_model,
        default_temperature=float(os.getenv("OLLAMA_TEMPERATURE", "0.2")),
        available_models_env=available_models_env,
        history_path=BASE_DIR / ".chat_history.json",
    )


def get_openai_settings() -> OpenAISettings:
    return OpenAISettings(
        api_key=os.getenv("OPENAI_API_KEY"),
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
    )