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
    default_context_window: int
    default_prompt_profile: str
    available_models_env: list[str]
    available_embedding_models_env: list[str]
    history_path: Path


@dataclass(frozen=True)
class OpenAISettings:
    api_key: str | None
    model: str
    default_context_window: int
    available_models_env: list[str]


@dataclass(frozen=True)
class RagSettings:
    embedding_model: str
    embedding_context_window: int
    embedding_truncate: bool
    chunk_size: int
    chunk_overlap: int
    top_k: int
    store_path: Path
    chroma_path: Path
    rerank_pool_size: int = 8
    rerank_lexical_weight: float = 0.35
    context_budget_ratio: float = 0.45
    context_chars_per_token: float = 4.0
    context_budget_min_chars: int = 1800
    context_budget_max_chars: int = 16000



def get_ollama_settings() -> OllamaSettings:
    default_model = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
    available_models_env = [
        model.strip()
        for model in os.getenv("OLLAMA_AVAILABLE_MODELS", "").split(",")
        if model.strip()
    ]
    available_embedding_models_env = [
        model.strip()
        for model in os.getenv("OLLAMA_AVAILABLE_EMBEDDING_MODELS", "").split(",")
        if model.strip()
    ]

    return OllamaSettings(
        project_name=os.getenv("PROJECT_NAME", "AI Workbench Local"),
        base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1"),
        default_model=default_model,
        default_temperature=float(os.getenv("OLLAMA_TEMPERATURE", "0.2")),
        default_context_window=int(os.getenv("OLLAMA_CONTEXT_WINDOW", "8192")),
        default_prompt_profile=os.getenv("DEFAULT_PROMPT_PROFILE", "neutro"),
        available_models_env=available_models_env,
        available_embedding_models_env=available_embedding_models_env,
        history_path=BASE_DIR / ".chat_history.json",
    )



def get_openai_settings() -> OpenAISettings:
    available_models_env = [
        model.strip()
        for model in os.getenv("OPENAI_AVAILABLE_MODELS", "").split(",")
        if model.strip()
    ]

    return OpenAISettings(
        api_key=os.getenv("OPENAI_API_KEY"),
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        default_context_window=int(os.getenv("OPENAI_CONTEXT_WINDOW", "128000")),
        available_models_env=available_models_env,
    )



def get_rag_settings() -> RagSettings:
    return RagSettings(
        embedding_model=os.getenv("OLLAMA_EMBEDDING_MODEL", "bge-m3"),
        embedding_context_window=int(os.getenv("OLLAMA_EMBEDDING_CONTEXT_WINDOW", "8192")),
        embedding_truncate=os.getenv("OLLAMA_EMBEDDING_TRUNCATE", "true").strip().lower() not in {"0", "false", "no"},
        chunk_size=int(os.getenv("RAG_CHUNK_SIZE", "1200")),
        chunk_overlap=int(os.getenv("RAG_CHUNK_OVERLAP", "200")),
        top_k=int(os.getenv("RAG_TOP_K", "4")),
        store_path=BASE_DIR / ".rag_store.json",
        chroma_path=BASE_DIR / ".chroma_rag",
        rerank_pool_size=int(os.getenv("RAG_RERANK_POOL_SIZE", "8")),
        rerank_lexical_weight=float(os.getenv("RAG_RERANK_LEXICAL_WEIGHT", "0.35")),
        context_budget_ratio=float(os.getenv("RAG_CONTEXT_BUDGET_RATIO", "0.45")),
        context_chars_per_token=float(os.getenv("RAG_CONTEXT_CHARS_PER_TOKEN", "4.0")),
        context_budget_min_chars=int(os.getenv("RAG_CONTEXT_BUDGET_MIN_CHARS", "1800")),
        context_budget_max_chars=int(os.getenv("RAG_CONTEXT_BUDGET_MAX_CHARS", "16000")),
    )
