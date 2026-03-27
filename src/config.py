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
    chunking_strategy: str
    embedding_model: str
    embedding_context_window: int
    embedding_truncate: bool
    chunk_size: int
    chunk_overlap: int
    top_k: int
    store_path: Path
    chroma_path: Path
    rerank_pool_size: int = 16
    rerank_lexical_weight: float = 0.35
    context_budget_ratio: float = 0.45
    context_chars_per_token: float = 4.0
    context_budget_min_chars: int = 1800
    context_budget_max_chars: int = 16000
    pdf_extraction_mode: str = "hybrid"
    pdf_baseline_chars_per_page_threshold: int = 90
    pdf_min_text_coverage_ratio: float = 0.65
    pdf_suspicious_image_count_threshold: int = 1
    pdf_suspicious_image_area_ratio: float = 0.18
    pdf_suspicious_low_text_chars: int = 220
    pdf_suspicious_page_score_threshold: float = 0.85
    pdf_suspicious_pages_trigger_full_docling_ratio: float = 0.45
    pdf_suspicious_pages_trigger_full_docling_min_count: int = 6
    pdf_max_selective_docling_pages: int = 12
    pdf_docling_enabled: bool = True
    pdf_docling_ocr_enabled: bool = True
    pdf_docling_force_full_page_ocr: bool = False
    pdf_docling_picture_description: bool = False
    pdf_ocr_fallback_enabled: bool = True
    pdf_ocr_fallback_min_chars: int = 120
    pdf_ocr_fallback_min_chars_per_page: int = 90
    pdf_ocr_fallback_languages: str = "eng+por"
    pdf_ocr_fallback_timeout_seconds: int = 180
    pdf_scan_image_ocr_enabled: bool = True
    pdf_scan_image_ocr_min_suspicious_ratio: float = 0.8
    pdf_scan_image_ocr_min_suspicious_count: int = 2
    pdf_scan_image_ocr_oversample_dpi: int = 300
    pdf_evidence_pipeline_enabled: bool = False
    pdf_evidence_pipeline_use_for_cv_like: bool = True
    pdf_evidence_pipeline_use_for_strong_scan_like: bool = True
    pdf_evidence_pipeline_min_scan_suspicious_ratio: float = 0.8
    pdf_evidence_pipeline_rollout_percentage: int = 100



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
        chunking_strategy=os.getenv("RAG_CHUNKING_STRATEGY", "manual").strip().lower() or "manual",
        embedding_model=os.getenv("OLLAMA_EMBEDDING_MODEL", "embeddinggemma:300m"),
        embedding_context_window=int(os.getenv("OLLAMA_EMBEDDING_CONTEXT_WINDOW", "512")),
        embedding_truncate=os.getenv("OLLAMA_EMBEDDING_TRUNCATE", "true").strip().lower() not in {"0", "false", "no"},
        chunk_size=int(os.getenv("RAG_CHUNK_SIZE", "1200")),
        chunk_overlap=int(os.getenv("RAG_CHUNK_OVERLAP", "80")),
        top_k=int(os.getenv("RAG_TOP_K", "6")),
        store_path=BASE_DIR / ".rag_store.json",
        chroma_path=BASE_DIR / ".chroma_rag",
        rerank_pool_size=int(os.getenv("RAG_RERANK_POOL_SIZE", "16")),
        rerank_lexical_weight=float(os.getenv("RAG_RERANK_LEXICAL_WEIGHT", "0.35")),
        context_budget_ratio=float(os.getenv("RAG_CONTEXT_BUDGET_RATIO", "0.45")),
        context_chars_per_token=float(os.getenv("RAG_CONTEXT_CHARS_PER_TOKEN", "4.0")),
        context_budget_min_chars=int(os.getenv("RAG_CONTEXT_BUDGET_MIN_CHARS", "1800")),
        context_budget_max_chars=int(os.getenv("RAG_CONTEXT_BUDGET_MAX_CHARS", "16000")),
        pdf_extraction_mode=os.getenv("RAG_PDF_EXTRACTION_MODE", "hybrid").strip().lower(),
        pdf_baseline_chars_per_page_threshold=int(os.getenv("RAG_PDF_BASELINE_CHARS_PER_PAGE_THRESHOLD", "90")),
        pdf_min_text_coverage_ratio=float(os.getenv("RAG_PDF_MIN_TEXT_COVERAGE_RATIO", "0.65")),
        pdf_suspicious_image_count_threshold=int(os.getenv("RAG_PDF_SUSPICIOUS_IMAGE_COUNT_THRESHOLD", "1")),
        pdf_suspicious_image_area_ratio=float(os.getenv("RAG_PDF_SUSPICIOUS_IMAGE_AREA_RATIO", "0.18")),
        pdf_suspicious_low_text_chars=int(os.getenv("RAG_PDF_SUSPICIOUS_LOW_TEXT_CHARS", "220")),
        pdf_suspicious_page_score_threshold=float(os.getenv("RAG_PDF_SUSPICIOUS_PAGE_SCORE_THRESHOLD", "0.85")),
        pdf_suspicious_pages_trigger_full_docling_ratio=float(os.getenv("RAG_PDF_SUSPICIOUS_PAGES_TRIGGER_FULL_DOCLING_RATIO", "0.45")),
        pdf_suspicious_pages_trigger_full_docling_min_count=int(os.getenv("RAG_PDF_SUSPICIOUS_PAGES_TRIGGER_FULL_DOCLING_MIN_COUNT", "6")),
        pdf_max_selective_docling_pages=int(os.getenv("RAG_PDF_MAX_SELECTIVE_DOCLING_PAGES", "12")),
        pdf_docling_enabled=os.getenv("RAG_PDF_DOCLING_ENABLED", "true").strip().lower() not in {"0", "false", "no"},
        pdf_docling_ocr_enabled=os.getenv("RAG_PDF_DOCLING_OCR_ENABLED", "true").strip().lower() not in {"0", "false", "no"},
        pdf_docling_force_full_page_ocr=os.getenv("RAG_PDF_DOCLING_FORCE_FULL_PAGE_OCR", "false").strip().lower() not in {"0", "false", "no"},
        pdf_docling_picture_description=os.getenv("RAG_PDF_DOCLING_PICTURE_DESCRIPTION", "false").strip().lower() not in {"0", "false", "no"},
        pdf_ocr_fallback_enabled=os.getenv("RAG_PDF_OCR_FALLBACK_ENABLED", "true").strip().lower() not in {"0", "false", "no"},
        pdf_ocr_fallback_min_chars=int(os.getenv("RAG_PDF_OCR_FALLBACK_MIN_CHARS", "120")),
        pdf_ocr_fallback_min_chars_per_page=int(os.getenv("RAG_PDF_OCR_FALLBACK_MIN_CHARS_PER_PAGE", "90")),
        pdf_ocr_fallback_languages=os.getenv("RAG_PDF_OCR_FALLBACK_LANGUAGES", "eng+por").strip() or "eng+por",
        pdf_ocr_fallback_timeout_seconds=int(os.getenv("RAG_PDF_OCR_FALLBACK_TIMEOUT_SECONDS", "180")),
        pdf_scan_image_ocr_enabled=os.getenv("RAG_PDF_SCAN_IMAGE_OCR_ENABLED", "true").strip().lower() not in {"0", "false", "no"},
        pdf_scan_image_ocr_min_suspicious_ratio=float(os.getenv("RAG_PDF_SCAN_IMAGE_OCR_MIN_SUSPICIOUS_RATIO", "0.8")),
        pdf_scan_image_ocr_min_suspicious_count=int(os.getenv("RAG_PDF_SCAN_IMAGE_OCR_MIN_SUSPICIOUS_COUNT", "2")),
        pdf_scan_image_ocr_oversample_dpi=int(os.getenv("RAG_PDF_SCAN_IMAGE_OCR_OVERSAMPLE_DPI", "300")),
        pdf_evidence_pipeline_enabled=os.getenv("RAG_PDF_EVIDENCE_PIPELINE_ENABLED", "false").strip().lower() not in {"0", "false", "no"},
        pdf_evidence_pipeline_use_for_cv_like=os.getenv("RAG_PDF_EVIDENCE_PIPELINE_USE_FOR_CV_LIKE", "true").strip().lower() not in {"0", "false", "no"},
        pdf_evidence_pipeline_use_for_strong_scan_like=os.getenv("RAG_PDF_EVIDENCE_PIPELINE_USE_FOR_STRONG_SCAN_LIKE", "true").strip().lower() not in {"0", "false", "no"},
        pdf_evidence_pipeline_min_scan_suspicious_ratio=float(os.getenv("RAG_PDF_EVIDENCE_PIPELINE_MIN_SCAN_SUSPICIOUS_RATIO", "0.8")),
        pdf_evidence_pipeline_rollout_percentage=max(0, min(100, int(os.getenv("RAG_PDF_EVIDENCE_PIPELINE_ROLLOUT_PERCENTAGE", "100")))),
    )
