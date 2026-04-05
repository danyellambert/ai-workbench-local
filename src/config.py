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
    default_top_p: float | None = None
    default_max_tokens: int | None = None


@dataclass(frozen=True)
class OpenAISettings:
    api_key: str | None
    model: str
    embedding_model: str
    default_context_window: int
    available_models_env: list[str]
    available_embedding_models_env: list[str]
    default_top_p: float | None = None
    default_max_tokens: int | None = None


@dataclass(frozen=True)
class HuggingFaceSettings:
    model: str
    embedding_model: str
    default_context_window: int
    available_models_env: list[str]
    available_embedding_models_env: list[str]
    generation_task: str
    max_new_tokens: int
    top_p: float | None = None


@dataclass(frozen=True)
class HuggingFaceServerSettings:
    base_url: str
    api_key: str | None
    model: str
    embedding_model: str
    default_context_window: int
    available_models_env: list[str]
    available_embedding_models_env: list[str]
    default_top_p: float | None = None
    default_max_tokens: int | None = None


@dataclass(frozen=True)
class HuggingFaceInferenceSettings:
    base_url: str
    api_key: str | None
    model: str
    embedding_model: str
    default_context_window: int
    available_models_env: list[str]
    available_embedding_models_env: list[str]
    default_top_p: float | None = None
    default_max_tokens: int | None = None


def _optional_float_env(name: str) -> float | None:
    raw_value = str(os.getenv(name, "")).strip()
    if not raw_value:
        return None
    return float(raw_value)


def _optional_int_env(name: str) -> int | None:
    raw_value = str(os.getenv(name, "")).strip()
    if not raw_value:
        return None
    return int(raw_value)


@dataclass(frozen=True)
class RagSettings:
    loader_strategy: str
    chunking_strategy: str
    retrieval_strategy: str
    embedding_provider: str
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
    evidence_vl_model: str = "sorc/qwen3.5-instruct:2b"
    evidence_ocr_backend: str = "ocrmypdf"
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


@dataclass(frozen=True)
class NextcloudWebDavSettings:
    base_url: str
    username: str
    app_password: str
    root_path: str


@dataclass(frozen=True)
class TrelloSettings:
    api_key: str
    token: str
    board_id: str
    list_open_id: str
    list_review_id: str
    list_approved_id: str
    list_done_id: str


@dataclass(frozen=True)
class NotionSettings:
    api_key: str
    database_id: str
    parent_page_id: str
    api_version: str = "2022-06-28"


@dataclass(frozen=True)
class PresentationExportSettings:
    enabled: bool
    base_url: str
    timeout_seconds: int
    remote_output_dir: str
    remote_preview_dir: str
    local_artifact_dir: Path
    include_review: bool = True
    preview_backend: str = "auto"
    require_real_previews: bool = False
    fail_on_regression: bool = False
    enabled_export_kinds: tuple[str, ...] = ()


@dataclass(frozen=True)
class GradioProductSettings:
    app_name: str
    server_name: str
    server_port: int
    theme: str
    default_workflow: str
    max_upload_files: int
    enable_deck_generation: bool = True
    show_ai_lab_entry: bool = True
    accent_color: str = "#6ae3ff"
    default_density: str = "comfortable"


@dataclass(frozen=True)
class EvidenceOpsExternalSettings:
    repository_backend: str
    external_sync_enabled: bool
    corpus_primary_root: Path
    corpus_public_root: Path
    nextcloud: NextcloudWebDavSettings
    trello: TrelloSettings
    notion: NotionSettings



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
        default_top_p=_optional_float_env("OLLAMA_TOP_P"),
        default_max_tokens=_optional_int_env("OLLAMA_MAX_TOKENS"),
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
    available_embedding_models_env = [
        model.strip()
        for model in os.getenv("OPENAI_AVAILABLE_EMBEDDING_MODELS", "").split(",")
        if model.strip()
    ]

    return OpenAISettings(
        api_key=os.getenv("OPENAI_API_KEY"),
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        embedding_model=os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"),
        default_context_window=int(os.getenv("OPENAI_CONTEXT_WINDOW", "128000")),
        default_top_p=_optional_float_env("OPENAI_TOP_P"),
        default_max_tokens=_optional_int_env("OPENAI_MAX_TOKENS"),
        available_models_env=available_models_env,
        available_embedding_models_env=available_embedding_models_env,
    )


def get_huggingface_settings() -> HuggingFaceSettings:
    available_models_env = [
        model.strip()
        for model in os.getenv("HUGGINGFACE_AVAILABLE_MODELS", "").split(",")
        if model.strip()
    ]
    available_embedding_models_env = [
        model.strip()
        for model in os.getenv("HUGGINGFACE_AVAILABLE_EMBEDDING_MODELS", "").split(",")
        if model.strip()
    ]

    return HuggingFaceSettings(
        model=os.getenv("HUGGINGFACE_MODEL", "").strip(),
        embedding_model=os.getenv("HUGGINGFACE_EMBEDDING_MODEL", "").strip(),
        default_context_window=int(os.getenv("HUGGINGFACE_CONTEXT_WINDOW", "8192")),
        available_models_env=available_models_env,
        available_embedding_models_env=available_embedding_models_env,
        generation_task=os.getenv("HUGGINGFACE_GENERATION_TASK", "text-generation").strip() or "text-generation",
        max_new_tokens=int(os.getenv("HUGGINGFACE_MAX_NEW_TOKENS", "512")),
        top_p=_optional_float_env("HUGGINGFACE_TOP_P"),
    )


def get_huggingface_server_settings() -> HuggingFaceServerSettings:
    available_models_env = [
        model.strip()
        for model in os.getenv("HUGGINGFACE_SERVER_AVAILABLE_MODELS", "").split(",")
        if model.strip()
    ]
    available_embedding_models_env = [
        model.strip()
        for model in os.getenv("HUGGINGFACE_SERVER_AVAILABLE_EMBEDDING_MODELS", "").split(",")
        if model.strip()
    ]

    return HuggingFaceServerSettings(
        base_url=os.getenv("HUGGINGFACE_SERVER_BASE_URL", "").strip(),
        api_key=os.getenv("HUGGINGFACE_SERVER_API_KEY"),
        model=os.getenv("HUGGINGFACE_SERVER_MODEL", "").strip(),
        embedding_model=os.getenv("HUGGINGFACE_SERVER_EMBEDDING_MODEL", "").strip(),
        default_context_window=int(os.getenv("HUGGINGFACE_SERVER_CONTEXT_WINDOW", "8192")),
        default_top_p=_optional_float_env("HUGGINGFACE_SERVER_TOP_P"),
        default_max_tokens=_optional_int_env("HUGGINGFACE_SERVER_MAX_TOKENS"),
        available_models_env=available_models_env,
        available_embedding_models_env=available_embedding_models_env,
    )


def get_huggingface_inference_settings() -> HuggingFaceInferenceSettings:
    available_models_env = [
        model.strip()
        for model in os.getenv("HUGGINGFACE_INFERENCE_AVAILABLE_MODELS", "").split(",")
        if model.strip()
    ]
    available_embedding_models_env = [
        model.strip()
        for model in os.getenv("HUGGINGFACE_INFERENCE_AVAILABLE_EMBEDDING_MODELS", "").split(",")
        if model.strip()
    ]

    return HuggingFaceInferenceSettings(
        base_url=os.getenv("HUGGINGFACE_INFERENCE_BASE_URL", "https://router.huggingface.co/v1").strip(),
        api_key=os.getenv("HUGGINGFACE_INFERENCE_API_KEY"),
        model=os.getenv("HUGGINGFACE_INFERENCE_MODEL", "").strip(),
        embedding_model=os.getenv("HUGGINGFACE_INFERENCE_EMBEDDING_MODEL", "").strip(),
        default_context_window=int(os.getenv("HUGGINGFACE_INFERENCE_CONTEXT_WINDOW", "8192")),
        default_top_p=_optional_float_env("HUGGINGFACE_INFERENCE_TOP_P"),
        default_max_tokens=_optional_int_env("HUGGINGFACE_INFERENCE_MAX_TOKENS"),
        available_models_env=available_models_env,
        available_embedding_models_env=available_embedding_models_env,
    )


def get_presentation_export_settings() -> PresentationExportSettings:
    enabled_export_kinds = tuple(
        value.strip()
        for value in os.getenv("PRESENTATION_EXPORT_ENABLED_EXPORT_KINDS", "").split(",")
        if value.strip()
    )
    return PresentationExportSettings(
        enabled=os.getenv("PRESENTATION_EXPORT_ENABLED", "false").strip().lower() in {"1", "true", "yes"},
        base_url=os.getenv("PRESENTATION_EXPORT_BASE_URL", "http://127.0.0.1:8787").strip(),
        timeout_seconds=int(os.getenv("PRESENTATION_EXPORT_TIMEOUT_SECONDS", "120")),
        remote_output_dir=(
            os.getenv("PRESENTATION_EXPORT_REMOTE_OUTPUT_DIR", "outputs/ai_workbench_exports").strip()
            or "outputs/ai_workbench_exports"
        ),
        remote_preview_dir=(
            os.getenv("PRESENTATION_EXPORT_REMOTE_PREVIEW_DIR", "outputs/ai_workbench_export_previews").strip()
            or "outputs/ai_workbench_export_previews"
        ),
        local_artifact_dir=Path(
            os.getenv(
                "PRESENTATION_EXPORT_LOCAL_ARTIFACT_DIR",
                str(BASE_DIR / "artifacts" / "presentation_exports"),
            )
        ),
        include_review=os.getenv("PRESENTATION_EXPORT_INCLUDE_REVIEW", "true").strip().lower() not in {"0", "false", "no"},
        preview_backend=os.getenv("PRESENTATION_EXPORT_PREVIEW_BACKEND", "auto").strip() or "auto",
        require_real_previews=os.getenv("PRESENTATION_EXPORT_REQUIRE_REAL_PREVIEWS", "false").strip().lower() in {"1", "true", "yes"},
        fail_on_regression=os.getenv("PRESENTATION_EXPORT_FAIL_ON_REGRESSION", "false").strip().lower() in {"1", "true", "yes"},
        enabled_export_kinds=enabled_export_kinds,
    )


def get_gradio_product_settings() -> GradioProductSettings:
    return GradioProductSettings(
        app_name=os.getenv("GRADIO_PRODUCT_APP_NAME", "AI Workbench Product").strip() or "AI Workbench Product",
        server_name=os.getenv("GRADIO_PRODUCT_SERVER_NAME", "127.0.0.1").strip() or "127.0.0.1",
        server_port=int(os.getenv("GRADIO_PRODUCT_SERVER_PORT", "7860")),
        theme=os.getenv("GRADIO_PRODUCT_THEME", "premium_dark").strip() or "premium_dark",
        default_workflow=os.getenv("GRADIO_PRODUCT_DEFAULT_WORKFLOW", "document_review").strip() or "document_review",
        max_upload_files=max(1, int(os.getenv("GRADIO_PRODUCT_MAX_UPLOAD_FILES", "6"))),
        enable_deck_generation=os.getenv("GRADIO_PRODUCT_ENABLE_DECK_GENERATION", "true").strip().lower() not in {"0", "false", "no"},
        show_ai_lab_entry=os.getenv("GRADIO_PRODUCT_SHOW_AI_LAB_ENTRY", "true").strip().lower() not in {"0", "false", "no"},
        accent_color=os.getenv("GRADIO_PRODUCT_ACCENT_COLOR", "#6ae3ff").strip() or "#6ae3ff",
        default_density=os.getenv("GRADIO_PRODUCT_DEFAULT_DENSITY", "comfortable").strip() or "comfortable",
    )


def get_evidenceops_external_settings() -> EvidenceOpsExternalSettings:
    external_sync_enabled = os.getenv("EVIDENCEOPS_EXTERNAL_SYNC_ENABLED", "false").strip().lower() in {"1", "true", "yes"}
    nextcloud_base_url = os.getenv("EVIDENCEOPS_NEXTCLOUD_BASE_URL", "").strip()
    nextcloud_username = os.getenv("EVIDENCEOPS_NEXTCLOUD_USERNAME", "").strip()
    nextcloud_app_password = os.getenv("EVIDENCEOPS_NEXTCLOUD_APP_PASSWORD", "").strip()
    configured_default_backend = (
        "nextcloud_webdav"
        if external_sync_enabled and nextcloud_base_url and nextcloud_username and nextcloud_app_password
        else "local"
    )
    corpus_primary_root = Path(
        os.getenv(
            "EVIDENCEOPS_CORPUS_PRIMARY_ROOT",
            str(BASE_DIR / "data" / "corpus_revisado" / "option_b_synthetic_premium"),
        )
    )
    corpus_public_root = Path(
        os.getenv(
            "EVIDENCEOPS_CORPUS_PUBLIC_ROOT",
            str(BASE_DIR / "data" / "corpus_revisado" / "option_a_public_corpus_v2"),
        )
    )
    return EvidenceOpsExternalSettings(
        repository_backend=os.getenv("EVIDENCEOPS_REPOSITORY_BACKEND", configured_default_backend).strip().lower() or configured_default_backend,
        external_sync_enabled=external_sync_enabled,
        corpus_primary_root=corpus_primary_root,
        corpus_public_root=corpus_public_root,
        nextcloud=NextcloudWebDavSettings(
            base_url=nextcloud_base_url,
            username=nextcloud_username,
            app_password=nextcloud_app_password,
            root_path=os.getenv("EVIDENCEOPS_NEXTCLOUD_ROOT_PATH", "/EvidenceOpsDemo").strip() or "/EvidenceOpsDemo",
        ),
        trello=TrelloSettings(
            api_key=os.getenv("EVIDENCEOPS_TRELLO_API_KEY", "").strip(),
            token=os.getenv("EVIDENCEOPS_TRELLO_TOKEN", "").strip(),
            board_id=os.getenv("EVIDENCEOPS_TRELLO_BOARD_ID", "").strip(),
            list_open_id=os.getenv("EVIDENCEOPS_TRELLO_LIST_OPEN_ID", "").strip(),
            list_review_id=os.getenv("EVIDENCEOPS_TRELLO_LIST_REVIEW_ID", "").strip(),
            list_approved_id=os.getenv("EVIDENCEOPS_TRELLO_LIST_APPROVED_ID", "").strip(),
            list_done_id=os.getenv("EVIDENCEOPS_TRELLO_LIST_DONE_ID", "").strip(),
        ),
        notion=NotionSettings(
            api_key=os.getenv("EVIDENCEOPS_NOTION_API_KEY", "").strip(),
            database_id=os.getenv("EVIDENCEOPS_NOTION_DATABASE_ID", "").strip(),
            parent_page_id=os.getenv("EVIDENCEOPS_NOTION_PARENT_PAGE_ID", "").strip(),
            api_version=os.getenv("EVIDENCEOPS_NOTION_API_VERSION", "2022-06-28").strip() or "2022-06-28",
        ),
    )



def get_rag_settings() -> RagSettings:
    embedding_provider = os.getenv("RAG_EMBEDDING_PROVIDER", "ollama").strip().lower() or "ollama"
    provider_default_embedding_model = (
        os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
        if embedding_provider == "openai"
        else os.getenv("HUGGINGFACE_SERVER_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
        if embedding_provider == "huggingface_server"
        else os.getenv("HUGGINGFACE_INFERENCE_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
        if embedding_provider == "huggingface_inference"
        else os.getenv("HUGGINGFACE_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
        if embedding_provider == "huggingface_local"
        else os.getenv("OLLAMA_EMBEDDING_MODEL", "embeddinggemma:300m")
    )
    embedding_context_window = int(
        os.getenv(
            "RAG_EMBEDDING_CONTEXT_WINDOW",
            os.getenv("OLLAMA_EMBEDDING_CONTEXT_WINDOW", "512"),
        )
    )
    embedding_truncate = os.getenv(
        "RAG_EMBEDDING_TRUNCATE",
        os.getenv("OLLAMA_EMBEDDING_TRUNCATE", "true"),
    ).strip().lower() not in {"0", "false", "no"}
    return RagSettings(
        loader_strategy=os.getenv("RAG_LOADER_STRATEGY", "manual").strip().lower() or "manual",
        chunking_strategy=os.getenv("RAG_CHUNKING_STRATEGY", "manual").strip().lower() or "manual",
        retrieval_strategy=os.getenv("RAG_RETRIEVAL_STRATEGY", "manual_hybrid").strip().lower() or "manual_hybrid",
        embedding_provider=embedding_provider,
        embedding_model=(os.getenv("RAG_EMBEDDING_MODEL", "").strip() or provider_default_embedding_model),
        embedding_context_window=embedding_context_window,
        embedding_truncate=embedding_truncate,
        chunk_size=int(os.getenv("RAG_CHUNK_SIZE", "1200")),
        chunk_overlap=int(os.getenv("RAG_CHUNK_OVERLAP", "80")),
        top_k=int(os.getenv("RAG_TOP_K", "6")),
        store_path=BASE_DIR / ".rag_store.json",
        chroma_path=BASE_DIR / ".chroma_rag",
        rerank_pool_size=int(os.getenv("RAG_RERANK_POOL_SIZE", "16")),
        rerank_lexical_weight=float(os.getenv("RAG_RERANK_LEXICAL_WEIGHT", "0.35")),
        evidence_vl_model=os.getenv("EVIDENCE_VL_MODEL", "sorc/qwen3.5-instruct:2b").strip() or "sorc/qwen3.5-instruct:2b",
        evidence_ocr_backend=os.getenv("EVIDENCE_OCR_BACKEND", "ocrmypdf").strip() or "ocrmypdf",
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
