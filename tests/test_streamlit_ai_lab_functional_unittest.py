import json
import logging
import mimetypes
import tempfile
import unittest
from contextlib import ExitStack, contextmanager
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import streamlit.logger as streamlit_logger
import streamlit.runtime.scriptrunner_utils.script_run_context as script_run_context
from streamlit.testing.v1 import AppTest


streamlit_logger.set_log_level("error")
script_run_context._LOGGER.setLevel(logging.ERROR)
script_run_context._LOGGER.disabled = True

from src.app.bootstrap import AppBootstrap
from src.config import OllamaSettings, PresentationExportSettings, RagSettings
from src.evidence_cv.config import build_evidence_config_from_rag_settings
from src.prompt_profiles import get_prompt_profiles
from src.providers.registry import build_embedding_provider_sidebar_state
from src.services.presentation_export import DEFAULT_PRESENTATION_EXPORT_KIND
from src.storage.runtime_paths import (
    get_phase55_langgraph_shadow_log_path,
    get_phase55_shadow_log_path,
    get_phase6_document_agent_log_path,
    get_phase7_model_comparison_log_path,
    get_phase95_evidenceops_worklog_path,
)
from src.structured.base import (
    AgentSource,
    AgentToolExecution,
    ChecklistItem,
    ChecklistPayload,
    CodeAnalysisPayload,
    CodeIssue,
    ComparisonFinding,
    ContactInfo,
    CVAnalysisPayload,
    DocumentAgentPayload,
    ExtractionPayload,
    SummaryPayload,
    Topic,
)
from src.structured.envelope import RenderMode, StructuredResult
from src.structured.registry import build_structured_task_registry


class _FakeProvider:
    def __init__(self) -> None:
        self.chat_calls: list[dict[str, object]] = []

    def list_available_models(self) -> list[str]:
        return ["fake-model-a", "fake-model-b"]

    def list_available_embedding_models(self) -> list[str]:
        return ["fake-embed"]

    def create_embeddings(self, texts: list[str], *, model: str, context_window: int, truncate: bool) -> list[list[float]]:
        embeddings: list[list[float]] = []
        for text in texts:
            normalized = str(text or "")
            base = sum(ord(char) for char in normalized) % 997
            embeddings.append([round(((base + offset * 17) % 100) / 100, 4) for offset in range(8)])
        return embeddings

    def stream_chat_completion(self, *, messages, model, temperature, context_window):
        self.chat_calls.append(
            {
                "messages": messages,
                "model": model,
                "temperature": temperature,
                "context_window": context_window,
            }
        )
        return ["Resposta ", "simulada do chat"]

    def iter_stream_text(self, stream):
        yield from stream

    def format_error(self, model: str, error: Exception) -> str:
        return f"{model}: {error}"

    def inspect_context_window(self, *, model: str, requested_context_window: int) -> dict[str, object]:
        return {
            "model": model,
            "requested_context_window": requested_context_window,
            "validated": True,
        }

    def inspect_embedding_context_window(self, *, model: str, requested_context_window: int) -> dict[str, object]:
        return {
            "model": model,
            "requested_context_window": requested_context_window,
            "validated": True,
        }


class _FakeUploadedFile:
    def __init__(self, name: str, content: bytes, mime_type: str = "text/plain") -> None:
        self.name = name
        self.type = mime_type
        self.size = len(content)
        self._content = content

    def getvalue(self) -> bytes:
        return self._content


class _FakeEvidenceOpsMcpClient:
    def __enter__(self):
        self._tool_names: list[str] = []
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def list_tools(self):
        self._tool_names.append("tools/list")
        return [{"name": "search_documents"}, {"name": "list_actions"}]

    def read_resource(self, uri: str):
        self._tool_names.append(f"resource:{uri}")
        return {"uri": uri, "documents": 1, "status": "ok"}

    def call_tool(self, name: str, arguments: dict | None = None):
        self._tool_names.append(name)
        arguments = arguments or {}
        if name == "compare_repository_state":
            return {"status": "ok", "documents": [{"document_id": "doc-1"}]}
        if name == "list_actions":
            return {"actions": [{"id": 1, "status": arguments.get("status", "open")}]}
        if name == "search_documents":
            return {"results": [{"document_id": "doc-1", "name": "Demo Policy"}]}
        return {"tool": name, "arguments": arguments}

    def telemetry_summary(self):
        return {
            "server_name": "fake-evidenceops-mcp",
            "transport": "stdio",
            "status": "success",
            "tool_call_count": len([item for item in self._tool_names if not item.startswith("resource:")]),
            "read_call_count": len([item for item in self._tool_names if item.startswith("resource:")]),
            "write_call_count": 1 if any(item == "update_action" for item in self._tool_names) else 0,
            "error_call_count": 0,
            "total_latency_s": 0.01,
            "tool_names": list(self._tool_names),
        }


class StreamlitAiLabFunctionalTests(unittest.TestCase):
    maxDiff = None

    def _write_json(self, path: Path, payload: object) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def _build_settings(self, temp_root: Path) -> tuple[OllamaSettings, RagSettings, PresentationExportSettings, _FakeProvider]:
        history_path = temp_root / ".runtime" / "state" / "chat" / "chat_history.json"
        rag_store_path = temp_root / ".runtime" / "state" / "rag" / "rag_store.json"
        chroma_path = temp_root / ".runtime" / "state" / "rag" / "chroma"
        provider = _FakeProvider()
        settings = OllamaSettings(
            project_name="AI Workbench Local",
            base_url="http://localhost:11434",
            default_model="fake-model-a",
            default_temperature=0.1,
            default_context_window=8192,
            default_prompt_profile="neutro",
            available_models_env=["fake-model-a", "fake-model-b"],
            available_embedding_models_env=["fake-embed"],
            history_path=history_path,
        )
        rag_settings = RagSettings(
            loader_strategy="manual",
            chunking_strategy="manual",
            retrieval_strategy="manual_hybrid",
            embedding_provider="ollama",
            embedding_model="fake-embed",
            embedding_context_window=512,
            embedding_truncate=True,
            chunk_size=1200,
            chunk_overlap=80,
            top_k=4,
            store_path=rag_store_path,
            chroma_path=chroma_path,
        )
        presentation_settings = PresentationExportSettings(
            enabled=True,
            base_url="http://renderer.test",
            timeout_seconds=5,
            remote_output_dir="/tmp/remote-output",
            remote_preview_dir="/tmp/remote-preview",
            local_artifact_dir=temp_root / "artifacts",
            enabled_export_kinds=(DEFAULT_PRESENTATION_EXPORT_KIND,),
        )
        return settings, rag_settings, presentation_settings, provider

    def _seed_runtime_files(self, temp_root: Path, rag_settings: RagSettings) -> None:
        rag_settings.store_path.parent.mkdir(parents=True, exist_ok=True)
        rag_settings.chroma_path.mkdir(parents=True, exist_ok=True)

        rag_store = {
            "documents": [
                {
                    "document_id": "doc-1",
                    "name": "demo.txt",
                    "file_type": "txt",
                    "file_hash": "hash-doc-1",
                    "char_count": 11,
                    "chunk_count": 1,
                    "indexed_at": "2026-04-08 10:00:00",
                    "loader_metadata": {
                        "loader_strategy_used": "manual",
                        "loader_strategy_label": "Local manual",
                        "chunking_strategy_used": "manual",
                        "chunking_strategy_label": "manual",
                    },
                }
            ],
            "chunks": [
                {
                    "document_id": "doc-1",
                    "chunk_id": 1,
                    "start_char": 0,
                    "end_char": 11,
                    "text": "hello world",
                    "snippet": "hello world",
                    "source": "demo.txt",
                    "file_type": "txt",
                    "embedding": [0.1, 0.2],
                }
            ],
            "settings": {
                "loader_strategy": rag_settings.loader_strategy,
                "chunking_strategy": rag_settings.chunking_strategy,
                "retrieval_strategy": rag_settings.retrieval_strategy,
                "embedding_provider": rag_settings.embedding_provider,
                "embedding_model": rag_settings.embedding_model,
                "embedding_context_window": rag_settings.embedding_context_window,
                "embedding_truncate": rag_settings.embedding_truncate,
                "chunk_size": rag_settings.chunk_size,
                "chunk_overlap": rag_settings.chunk_overlap,
                "top_k": rag_settings.top_k,
                "pdf_extraction_mode": rag_settings.pdf_extraction_mode,
            },
            "updated_at": "2026-04-08 10:00:00",
        }
        self._write_json(rag_settings.store_path, rag_store)

        self._write_json(
            get_phase55_shadow_log_path(temp_root),
            [
                {
                    "timestamp": "2026-04-08 10:01:00",
                    "query": "compare retrieval",
                    "primary_strategy": "manual_hybrid",
                    "alternate_strategy": "langchain_chroma",
                    "overlap_ratio": 1.0,
                    "same_top_1": True,
                    "same_top_3_order": True,
                }
            ],
        )
        self._write_json(
            get_phase55_langgraph_shadow_log_path(temp_root),
            [
                {
                    "timestamp": "2026-04-08 10:02:00",
                    "task_type": "summary",
                    "strategy_primary": "direct",
                    "strategy_alternate": "langgraph_context_retry",
                }
            ],
        )
        self._write_json(
            get_phase6_document_agent_log_path(temp_root),
            [
                {
                    "timestamp": "2026-04-08 10:03:00",
                    "intent": "document_risk_review",
                    "tool": "review_document_risks",
                }
            ],
        )
        self._write_json(
            get_phase7_model_comparison_log_path(temp_root),
            [
                {
                    "benchmark_use_case": "executive_summary",
                    "prompt_profile": "neutro",
                    "response_format": "bullet_list",
                    "retrieval_strategy": "manual_hybrid",
                    "embedding_provider": "ollama",
                    "embedding_model": "fake-embed",
                    "use_documents": False,
                    "aggregate": {
                        "total_candidates": 2,
                        "success_rate": 1.0,
                        "avg_latency_s": 0.5,
                        "avg_output_chars": 100.0,
                        "avg_format_adherence": 1.0,
                        "avg_groundedness_score": 0.8,
                        "avg_schema_adherence": 1.0,
                        "avg_use_case_fit_score": 0.9,
                    },
                    "candidate_results": [
                        {
                            "provider_effective": "ollama",
                            "model_effective": "fake-model-a",
                            "runtime_bucket": "local",
                            "quantization_family": "unspecified_local",
                            "success": True,
                            "latency_s": 0.4,
                            "output_chars": 100,
                            "format_adherence": 1.0,
                            "groundedness_score": 0.8,
                            "schema_adherence": 1.0,
                            "use_case_fit_score": 0.9,
                        },
                        {
                            "provider_effective": "ollama",
                            "model_effective": "fake-model-b",
                            "runtime_bucket": "local",
                            "quantization_family": "unspecified_local",
                            "success": True,
                            "latency_s": 0.6,
                            "output_chars": 90,
                            "format_adherence": 1.0,
                            "groundedness_score": 0.7,
                            "schema_adherence": 1.0,
                            "use_case_fit_score": 0.85,
                        },
                    ],
                }
            ],
        )
        self._write_json(get_phase95_evidenceops_worklog_path(temp_root), [])

    def _fake_bootstrap(
        self,
        temp_root: Path,
        *,
        rag_settings_transform=None,
    ) -> tuple[AppBootstrap, PresentationExportSettings, _FakeProvider, RagSettings]:
        settings, rag_settings, presentation_settings, provider = self._build_settings(temp_root)
        if callable(rag_settings_transform):
            rag_settings = rag_settings_transform(rag_settings)
        registry = {
            "ollama": {
                "label": "Ollama (local)",
                "detail": "Base URL: `http://localhost:11434`",
                "instance": provider,
                "supports_chat": True,
                "supports_embeddings": True,
                "default_model": "fake-model-a",
                "default_context_window": 8192,
            }
        }
        bootstrap = AppBootstrap(
            settings=settings,
            rag_settings=rag_settings,
            evidence_config=build_evidence_config_from_rag_settings(rag_settings),
            provider_registry=registry,
            prompt_profiles=get_prompt_profiles(),
            structured_task_registry=build_structured_task_registry(),
            embedding_sidebar_state=build_embedding_provider_sidebar_state(registry),
        )
        return bootstrap, presentation_settings, provider, rag_settings

    def _build_real_uploaded_file(self, relative_path: str) -> _FakeUploadedFile:
        path = Path(relative_path)
        mime_type = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
        return _FakeUploadedFile(path.name, path.read_bytes(), mime_type=mime_type)

    def _make_structured_result(self, *, task_type: str = "summary", strategy: str = "direct") -> StructuredResult:
        if task_type == "extraction":
            payload = ExtractionPayload(main_subject="Documento de teste", categories=["demo"])
        elif task_type == "checklist":
            payload = ChecklistPayload(
                title="Checklist demo",
                description="Checklist gerado para teste.",
                items=[
                    ChecklistItem(
                        title="Validar documento",
                        description="Confirmar se o documento foi revisado.",
                    )
                ],
                total_items=1,
                completed_items=0,
                progress_percentage=0.0,
            )
        elif task_type == "cv_analysis":
            payload = CVAnalysisPayload(
                personal_info=ContactInfo(
                    full_name="Ada Demo",
                    email="ada@example.com",
                    location="São Paulo",
                ),
                skills=["Python", "RAG"],
                languages=["Português", "English (advanced)"],
                strengths=["Grounded analysis"],
                improvement_areas=["Add more quantified impact"],
                projects=["AI Workbench"],
            )
        elif task_type == "code_analysis":
            payload = CodeAnalysisPayload(
                snippet_summary="Snippet de teste",
                main_purpose="Demonstrar a análise estruturada",
                detected_issues=[
                    CodeIssue(
                        severity="low",
                        category="readability",
                        title="Nome genérico",
                        description="Uma variável pode ganhar um nome mais descritivo.",
                        recommendation="Renomear a variável para um nome semântico.",
                    )
                ],
                readability_improvements=["Usar nomes mais explícitos"],
                maintainability_improvements=["Extrair função auxiliar"],
                refactor_plan=["Passo 1", "Passo 2"],
                test_suggestions=["Adicionar teste unitário"],
                risk_notes=["Baixo risco operacional"],
            )
        elif task_type == "document_agent":
            payload = DocumentAgentPayload(
                user_intent="document_risk_review",
                answer_mode="friendly",
                tool_used="review_document_risks",
                summary="Resumo do agente documental para teste.",
                key_points=["Ponto crítico identificado"],
                limitations=["Contexto simplificado para teste"],
                recommended_actions=["Escalar para revisão jurídica"],
                guardrails_applied=["grounded_sources"],
                available_tools=[{"tool_name": "review_document_risks"}],
                comparison_findings=[
                    ComparisonFinding(
                        finding_type="risk",
                        title="Risk finding",
                        description="A clause requires manual review.",
                        documents=["doc-1"],
                        evidence=["hello world"],
                    )
                ],
                structured_response={
                    "review_type": "risk_gap_review",
                    "extraction_payload": {
                        "action_items": [
                            {
                                "description": "Request clause review",
                                "owner": "Legal",
                                "due_date": "2026-05-01",
                                "status": "open",
                                "evidence": "hello world",
                            }
                        ],
                        "risks": [
                            {
                                "description": "Potential clause ambiguity",
                                "evidence": "hello world",
                            }
                        ],
                    },
                    "gaps": ["Missing approval chain"],
                    "restrictions": ["Do not auto-approve without legal review"],
                },
                sources=[
                    AgentSource(
                        source="demo.txt",
                        document_id="doc-1",
                        file_type="txt",
                        chunk_id=1,
                        score=0.9,
                        snippet="hello world",
                    )
                ],
                tool_runs=[
                    AgentToolExecution(
                        tool_name="review_document_risks",
                        status="success",
                        detail="Executed in mocked runtime.",
                    )
                ],
                confidence=0.9,
                needs_review=False,
            )
        else:
            payload = SummaryPayload(
                executive_summary="Resumo executivo simulado.",
                key_insights=["Insight A", "Insight B"],
                reading_time_minutes=1,
                completeness_score=0.95,
                topics=[
                    Topic(
                        title="Tema principal",
                        key_points=["Ponto 1"],
                        relevance_score=0.9,
                        supporting_evidence=["Trecho com evidência"],
                    )
                ],
            )
        return StructuredResult(
            success=True,
            task_type=task_type,
            raw_output_text=json.dumps(payload.model_dump(mode="json"), ensure_ascii=False),
            parsed_json=payload.model_dump(mode="json"),
            validated_output=payload,
            source_documents=["doc-1"],
            context_used=True,
            execution_metadata={
                "provider": "ollama",
                "model": "fake-model-a",
                "execution_strategy_used": strategy,
                "workflow_total_s": 0.15,
                "context_chars_sent": 42,
                "telemetry": {
                    "timings_s": {"total_s": 0.15, "provider_total_s": 0.08},
                    "provider_calls": [],
                },
            },
            available_render_modes=[
                RenderMode(mode="friendly", label="Friendly", available=True, priority=0),
                RenderMode(mode="json", label="JSON", available=True, priority=1),
            ],
            primary_render_mode="friendly",
            quality_score=0.95,
        )

    @contextmanager
    def _app_context(
        self,
        *,
        uploaded_files: list[_FakeUploadedFile] | None = None,
        patch_document_mutations: bool = False,
        rag_settings_transform=None,
    ):
        with tempfile.TemporaryDirectory() as tmp_dir, ExitStack() as stack:
            temp_root = Path(tmp_dir)
            bootstrap, presentation_settings, provider, rag_settings = self._fake_bootstrap(
                temp_root,
                rag_settings_transform=rag_settings_transform,
            )
            self._seed_runtime_files(temp_root, rag_settings)

            deck_artifact_dir = presentation_settings.local_artifact_dir / "deck-export-001"
            deck_artifact_dir.mkdir(parents=True, exist_ok=True)
            pptx_path = deck_artifact_dir / "review_deck.pptx"
            contract_path = deck_artifact_dir / "contract.json"
            payload_path = deck_artifact_dir / "payload.json"
            metadata_path = deck_artifact_dir / "metadata.json"
            pptx_path.write_bytes(b"fake-pptx")
            contract_path.write_text(json.dumps({"contract": True}), encoding="utf-8")
            payload_path.write_text(json.dumps({"payload": True}), encoding="utf-8")
            metadata_path.write_text(json.dumps({"export_id": "deck-export-001"}), encoding="utf-8")

            fake_deck_result = {
                "status": "completed",
                "export_id": "deck-export-001",
                "export_kind_label": DEFAULT_PRESENTATION_EXPORT_KIND,
                "model_comparison_entry_count": 1,
                "eval_entry_count": 0,
                "pptx_size_bytes": len(b"fake-pptx"),
                "service_health": "ok",
                "render_latency_s": 0.2,
                "artifact_download_latency_s": 0.1,
                "remote_output_path": "/tmp/remote-output/review_deck.pptx",
                "local_artifact_dir": str(deck_artifact_dir),
                "local_pptx_path": str(pptx_path),
                "local_contract_path": str(contract_path),
                "local_payload_path": str(payload_path),
            }

            def _fake_inject_rag_context(messages, retrieved_chunks, context_window, settings):
                return messages, {
                    "budget_chars": 1600,
                    "used_chars": 42,
                    "used_chunks": len(retrieved_chunks),
                    "dropped_chunks": 0,
                    "truncated": False,
                    "context_injected": bool(retrieved_chunks),
                    "context_chunks": list(retrieved_chunks),
                }

            def _fake_retrieve_relevant_chunks_detailed(*args, **kwargs):
                return {
                    "chunks": [
                        {
                            "source": "demo.txt",
                            "snippet": "hello world",
                            "text": "hello world",
                            "score": 0.9,
                            "vector_score": 0.9,
                            "lexical_score": 0.8,
                            "chunk_id": 1,
                            "document_id": "doc-1",
                        }
                    ],
                    "backend_used": "local",
                    "backend_message": "ok",
                    "vector_backend_status": {"status": "synced"},
                    "filtered_chunks_available": 1,
                    "candidate_pool_size": 1,
                    "rerank_strategy": "hybrid",
                    "retrieval_strategy_requested": "manual_hybrid",
                    "retrieval_strategy_used": "manual_hybrid",
                }

            def _fake_structured_workflow(request, strategy="direct"):
                return self._make_structured_result(task_type=request.task_type, strategy=strategy)

            def _fake_model_candidate(*, provider_name, model_name, **kwargs):
                latency = 0.4 if model_name == "fake-model-a" else 0.6
                return {
                    "provider_requested": provider_name,
                    "provider_effective": provider_name,
                    "model_requested": model_name,
                    "model_effective": model_name,
                    "runtime_bucket": "local",
                    "quantization_family": "unspecified_local",
                    "success": True,
                    "latency_s": latency,
                    "output_chars": 120 if model_name == "fake-model-a" else 110,
                    "format_adherence": 1.0,
                    "groundedness_score": 0.8,
                    "schema_adherence": 1.0,
                    "use_case_fit_score": 0.9 if model_name == "fake-model-a" else 0.85,
                    "response_text": f"Resultado simulado para {model_name}",
                }

            common_patches = {
                "bootstrap": patch("src.app.bootstrap.build_app_bootstrap", return_value=bootstrap),
                "presentation_settings": patch("src.config.get_presentation_export_settings", return_value=presentation_settings),
                "inject_rag_context": patch("src.rag.prompting.inject_rag_context", side_effect=_fake_inject_rag_context),
                "retrieve_relevant_chunks": patch("src.rag.service.retrieve_relevant_chunks_detailed", side_effect=_fake_retrieve_relevant_chunks_detailed),
                "structured_workflow": patch("src.structured.langgraph_workflow.run_structured_execution_workflow", side_effect=_fake_structured_workflow),
                "model_candidate": patch("src.services.model_comparison.run_model_comparison_candidate", side_effect=_fake_model_candidate),
                "deck_export": patch("src.ui.executive_deck_generation.generate_executive_deck", return_value=fake_deck_result),
                "document_context": patch("src.services.document_context.build_structured_document_context", return_value="[Source: demo.txt]\nhello world"),
                "inspect_vector_backend_status": patch(
                    "src.rag.service.inspect_vector_backend_status",
                    return_value={
                        "status": "synced",
                        "json_chunks": 1,
                        "chroma_chunks": 1,
                        "persist_dir": str(rag_settings.chroma_path),
                        "persist_dir_exists": True,
                        "message": "Vector backend synchronized.",
                    },
                ),
                "embedding_compatibility": patch(
                    "src.rag.service.inspect_embedding_configuration_compatibility",
                    return_value={"compatible": True, "message": "Embedding configuration is compatible."},
                ),
                "budget_decision": patch(
                    "src.services.runtime_budgeting.build_budget_routing_decision",
                    side_effect=lambda **kwargs: {
                        "routing_mode": "quality_first",
                        "reason": "test",
                        "sensitivity": kwargs.get("task_type", "generic"),
                        "quality_floor": "high",
                        "auto_degrade_applied": False,
                        "top_k_effective": kwargs.get("requested_top_k", 4),
                        "rerank_pool_size_effective": kwargs.get("requested_rerank_pool_size", 8),
                        "requested_top_k": kwargs.get("requested_top_k", 4),
                        "context_budget_chars": kwargs.get("context_budget_chars", 1600),
                        "estimated_context_chars": kwargs.get("estimated_context_chars", 42),
                        "context_pressure_ratio": 0.2,
                    },
                ),
                "quality_gate": patch(
                    "src.services.runtime_budgeting.assess_budget_quality_gate",
                    return_value={
                        "status": "pass",
                        "reason": "test",
                        "pass_rate": 1.0,
                        "min_pass_rate": 0.8,
                        "recent_runs": 5,
                    },
                ),
                "provider_routing": patch(
                    "src.services.runtime_budgeting.resolve_budget_provider_routing",
                    side_effect=lambda **kwargs: {
                        "effective_provider": kwargs.get("selected_provider"),
                        "provider_switch_applied": False,
                        "reason": "no_switch",
                    },
                ),
                "budget_alerts": patch(
                    "src.services.runtime_budgeting.evaluate_budget_alerts",
                    return_value={"status": "ok", "alerts": [], "thresholds": {}},
                ),
                "usage_metrics": patch(
                    "src.services.runtime_economics.estimate_runtime_usage_metrics",
                    side_effect=lambda **kwargs: {
                        "prompt_chars": int(kwargs.get("prompt_chars") or 0),
                        "output_chars": int(kwargs.get("completion_chars") or 0),
                        "context_chars": int(kwargs.get("context_chars") or 0),
                        "prompt_tokens": 10,
                        "completion_tokens": 6,
                        "total_tokens": 16,
                        "cost_usd": 0.0,
                        "usage_source": "estimated_chars",
                        "cost_source": "not_configured",
                        "native_usage_available": False,
                    },
                ),
                "native_usage": patch("src.services.runtime_economics.get_provider_native_usage_metrics", return_value=None),
                "aggregate_native_usage": patch("src.services.runtime_economics.aggregate_provider_call_native_usage", return_value=None),
                "external_status": patch(
                    "src.ui.evidenceops_mcp_panel.build_external_targets_status",
                    return_value={
                        "nextcloud": {"configured": True, "missing": []},
                        "trello": {"configured": True, "missing": []},
                        "notion": {"configured": True, "missing": []},
                    },
                ),
                "mcp_client": patch("src.ui.evidenceops_mcp_panel.EvidenceOpsMcpClient", _FakeEvidenceOpsMcpClient),
                "nextcloud_plan": patch(
                    "src.ui.evidenceops_mcp_panel.sync_phase95_corpus_to_nextcloud",
                    side_effect=lambda dry_run: {"planned_uploads": [{"name": "doc-1"}], "dry_run": dry_run},
                ),
                "register_evidenceops_entry": patch(
                    "src.services.evidenceops_mcp_client.register_evidenceops_entry_via_mcp",
                    return_value=(
                        {"actions_inserted": 1, "worklog_total_runs": 1},
                        {
                            "server_name": "fake-evidenceops-mcp",
                            "transport": "stdio",
                            "status": "success",
                            "tool_call_count": 1,
                            "read_call_count": 0,
                            "write_call_count": 1,
                            "error_call_count": 0,
                            "total_latency_s": 0.01,
                            "tool_names": ["register_evidenceops_entry"],
                        },
                    ),
                ),
                "trello_plan": patch(
                    "src.ui.evidenceops_mcp_panel.build_trello_storyline_cards",
                    side_effect=lambda dry_run: {"planned_cards": [{"title": "Storyline"}], "dry_run": dry_run},
                ),
                "notion_plan": patch(
                    "src.ui.evidenceops_mcp_panel.build_notion_storyline_register_entries",
                    side_effect=lambda dry_run: {"planned_pages": [{"title": "Register"}], "dry_run": dry_run},
                ),
                "remote_docs": patch(
                    "src.ui.evidenceops_mcp_panel.list_nextcloud_repository_documents",
                    return_value=[{"document_id": "remote-1", "name": "Remote policy"}],
                ),
                "update_action": patch(
                    "src.ui.evidenceops_mcp_panel.update_evidenceops_action_via_mcp",
                    return_value=(
                        {"action_id": 1, "status": "closed", "approval_status": "approved"},
                        {
                            "server_name": "fake-evidenceops-mcp",
                            "transport": "stdio",
                            "status": "success",
                            "tool_call_count": 1,
                            "read_call_count": 0,
                            "write_call_count": 1,
                            "error_call_count": 0,
                            "total_latency_s": 0.01,
                            "tool_names": ["update_action"],
                        },
                    ),
                ),
            }

            if uploaded_files is not None:
                common_patches["file_uploader"] = patch("streamlit.file_uploader", return_value=uploaded_files)

            if patch_document_mutations:
                common_patches["remove_documents"] = patch(
                    "src.rag.service.remove_documents_from_rag_index",
                    return_value=(None, {"ok": True, "message": "Documents removed."}),
                )
                common_patches["clear_index"] = patch(
                    "src.rag.service.clear_persisted_rag_index",
                    return_value={"ok": True, "message": "Index cleared."},
                )
                common_patches["reset_chroma"] = patch(
                    "src.rag.service.reset_chroma_persist_directory",
                    return_value={"ok": True, "message": "Chroma reset."},
                )

            mocks = SimpleNamespace(**{name: stack.enter_context(patcher) for name, patcher in common_patches.items()})
            app = AppTest.from_file("legacy/entrypoints/main_streamlit_lab.py")
            app.run(timeout=30)
            yield app, temp_root, mocks, provider, rag_settings

    def _button_by_label(self, app: AppTest, label: str):
        for button in app.button:
            if button.label == label:
                return button
        self.fail(f"Button not found: {label}")

    def _selectbox_by_label(self, app: AppTest, label: str):
        for selectbox in app.selectbox:
            if selectbox.label == label:
                return selectbox
        self.fail(f"Selectbox not found: {label}")

    def _text_area_by_label(self, app: AppTest, label: str):
        for text_area in app.text_area:
            if text_area.label == label:
                return text_area
        self.fail(f"Text area not found: {label}")

    def _text_input_by_label(self, app: AppTest, label: str):
        for text_input in app.text_input:
            if text_input.label == label:
                return text_input
        self.fail(f"Text input not found: {label}")

    def _multiselect_by_label(self, app: AppTest, label: str):
        for multiselect in app.multiselect:
            if multiselect.label == label:
                return multiselect
        self.fail(f"Multiselect not found: {label}")

    def _checkbox_by_label(self, app: AppTest, label: str):
        for checkbox in app.checkbox:
            if checkbox.label == label:
                return checkbox
        self.fail(f"Checkbox not found: {label}")

    def _slider_by_label(self, app: AppTest, label: str):
        for slider in app.slider:
            if slider.label == label:
                return slider
        self.fail(f"Slider not found: {label}")

    def _number_input_by_label(self, app: AppTest, label: str):
        for number_input in app.number_input:
            if number_input.label == label:
                return number_input
        self.fail(f"Number input not found: {label}")

    def _radio_by_label(self, app: AppTest, label: str):
        for radio in app.radio:
            if radio.label == label:
                return radio
        self.fail(f"Radio not found: {label}")

    def test_chat_flow_and_clear_conversation_work(self) -> None:
        with self._app_context() as (app, _temp_root, mocks, provider, _rag_settings):
            app.chat_input[0].set_value("Explique o documento de teste").run(timeout=30)

            self.assertEqual(len(app.exception), 0)
            self.assertTrue(mocks.retrieve_relevant_chunks.called)
            self.assertGreaterEqual(len(provider.chat_calls), 1)

            state = app.session_state.filtered_state
            messages = state.get("lista_mensagens") or []
            self.assertGreaterEqual(len(messages), 2)
            self.assertEqual(messages[-2]["role"], "user")
            self.assertEqual(messages[-1]["role"], "assistant")
            self.assertIn("Resposta simulada do chat", messages[-1]["content"])

            self._button_by_label(app, "🧹 Clear conversation").click().run(timeout=30)
            self.assertEqual(app.session_state.filtered_state.get("lista_mensagens") or [], [])

    def test_index_button_processes_uploaded_files_when_uploads_are_present(self) -> None:
        uploaded_files = [_FakeUploadedFile("demo_upload.txt", b"hello upload")]
        with self._app_context(uploaded_files=uploaded_files) as (app, _temp_root, mocks, _provider, _rag_settings):
            fake_loaded_document = MagicMock()
            fake_built_index = {
                "documents": [{"document_id": "doc-upload", "name": "demo_upload.txt", "file_type": "txt", "chunk_count": 1, "char_count": 12}],
                "chunks": [{"document_id": "doc-upload", "chunk_id": 1, "text": "hello upload", "source": "demo_upload.txt"}],
                "settings": {},
                "updated_at": "2026-04-08 12:00:00",
            }
            with (
                patch("src.rag.loaders.load_document", return_value=fake_loaded_document) as load_document_mock,
                patch(
                    "src.rag.service.upsert_documents_in_rag_index",
                    return_value=(fake_built_index, {"ok": True, "message": "Indexed successfully."}),
                ) as upsert_mock,
            ):
                self._button_by_label(app, "📚 Indexar / reindexar uploads").click().run(timeout=30)

            self.assertEqual(len(app.exception), 0)
            load_document_mock.assert_called()
            upsert_mock.assert_called()

    def test_index_button_processes_real_pdf_txt_csv_md_py_files(self) -> None:
        uploaded_files = [
            self._build_real_uploaded_file("data/corpus_revisado/option_b_synthetic_premium/policies/POL-001_Information_Security_Policy_v1.pdf"),
            self._build_real_uploaded_file("data/corpus_revisado/option_b_synthetic_premium/README_plus_metadata.txt"),
            self._build_real_uploaded_file("data/corpus_revisado/option_b_storylines.csv"),
            self._build_real_uploaded_file("data/corpus_revisado/option_a_public_corpus_v2/contracts_and_procurement/common_paper_sla.md"),
            self._build_real_uploaded_file("legacy/entrypoints/main_streamlit_lab.py"),
        ]

        def _rag_settings_transform(rag_settings: RagSettings) -> RagSettings:
            return replace(
                rag_settings,
                pdf_extraction_mode="basic",
                pdf_docling_enabled=False,
                pdf_docling_ocr_enabled=False,
                pdf_ocr_fallback_enabled=False,
            )

        with self._app_context(
            uploaded_files=uploaded_files,
            rag_settings_transform=_rag_settings_transform,
        ) as (app, _temp_root, _mocks, _provider, rag_settings):
            with patch(
                "src.rag.service.sync_chroma_from_rag_index",
                return_value={"ok": True, "message": "Chroma sync skipped in test.", "backend": "skipped"},
            ):
                self._multiselect_by_label(
                    app,
                    "Selecionar uploads para indexar/reindexar agora",
                ).set_value([uploaded_file.name for uploaded_file in uploaded_files]).run(timeout=60)
                self._button_by_label(app, "📚 Indexar / reindexar uploads").click().run(timeout=90)

            self.assertEqual(len(app.exception), 0)
            stored_payload = json.loads(rag_settings.store_path.read_text(encoding="utf-8"))
            document_names = {str(item.get("name")) for item in stored_payload.get("documents") or []}
            file_types = {str(item.get("file_type")) for item in stored_payload.get("documents") or []}
            self.assertTrue({uploaded_file.name for uploaded_file in uploaded_files}.issubset(document_names))
            self.assertTrue({"pdf", "txt", "csv", "md", "py"}.issubset(file_types))

    def test_structured_analysis_runs_and_persists_result(self) -> None:
        with self._app_context() as (app, _temp_root, mocks, _provider, _rag_settings):
            self._selectbox_by_label(app, "Task").set_value("summary").run(timeout=30)
            self._checkbox_by_label(app, "Usar documentos selecionados").set_value(False).run(timeout=30)
            self._text_area_by_label(app, "Input text (opcional quando usar documentos)").set_value("Resuma este texto de teste.").run(timeout=30)
            self._button_by_label(app, "Run structured analysis").click().run(timeout=30)

            self.assertEqual(len(app.exception), 0)
            self.assertTrue(mocks.structured_workflow.called)
            state = app.session_state.filtered_state
            stored = state.get("phase5_structured_result")
            self.assertIsInstance(stored, dict)
            self.assertEqual(stored.get("task_type"), "summary")
            self.assertTrue(stored.get("success"))

    def test_all_visible_inputs_accept_alternative_values(self) -> None:
        selectbox_raw_value_matrix = {
            "Provider": ["all", "ollama"],
            "Model": ["all", "fake-model-a", "fake-model-b"],
            "Use case": ["all", "Executive summary"],
            "Outcome": ["all", "success_only", "failures_only"],
            "Caso de uso do benchmark": [
                "ad_hoc",
                "executive_summary",
                "risk_review",
                "policy_compliance",
                "structured_extraction",
                "technical_review",
            ],
            "Perfil de prompt da comparação": ["neutro", "programador", "professor", "resumidor", "extrator"],
            "Formato desejado da resposta": ["plain_text", "bullet_list", "json"],
            "Novo status": ["open", "in_progress", "pending", "closed"],
            "Modelo de geração": ["fake-model-a", "fake-model-b"],
            "Perfil de prompt": ["neutro", "programador", "professor", "resumidor", "extrator"],
            "Loader strategy": ["manual", "langchain_basic"],
            "Chunking strategy": ["manual", "langchain_recursive"],
            "Retrieval strategy": ["manual_hybrid", "langchain_chroma"],
            "Extração de PDF": ["basic", "hybrid", "complete"],
            "Backend de OCR documental": ["ocrmypdf", "docling"],
        }
        uploaded_files = [
            _FakeUploadedFile("demo_upload_a.txt", b"hello upload a"),
            _FakeUploadedFile("demo_upload_b.txt", b"hello upload b"),
        ]
        with self._app_context(uploaded_files=uploaded_files) as (app, _temp_root, _mocks, _provider, _rag_settings):
            self._radio_by_label(app, "Modo da janela de contexto").set_value("manual").run(timeout=30)

            for slider_label in [
                "Janela de contexto da geração",
                "Temperatura",
                "Janela de contexto do embedding",
                "Chunk size",
                "Chunk overlap",
                "Retrieval top-k",
                "Reranking pool",
                "Lexical weight in reranking",
            ]:
                slider = self._slider_by_label(app, slider_label)
                minimum = getattr(slider.proto, "min", slider.value)
                maximum = getattr(slider.proto, "max", slider.value)
                target = maximum if slider.value != maximum else minimum
                slider.set_value(target).run(timeout=30)

            self._text_input_by_label(app, "Modelo VLM documental").set_value("demo-vlm-model").run(timeout=30)
            self._text_input_by_label(app, "Buscar documentos via MCP").set_value("contract review").run(timeout=30)
            self._text_input_by_label(app, "Motivo da aprovação").set_value("Validated in simulation").run(timeout=30)
            self._text_input_by_label(app, "Aprovado por").set_value("qa-user").run(timeout=30)
            self._number_input_by_label(app, "ID da ação").set_value(7).run(timeout=30)

            self._text_area_by_label(app, "Input text (opcional quando usar documentos)").set_value("Texto alternativo para structured analysis").run(timeout=30)
            self._text_area_by_label(app, "Prompt para comparar").set_value("Prompt alternativo de benchmark").run(timeout=30)

            self._multiselect_by_label(app, "Selecionar uploads para indexar/reindexar agora").set_value(["demo_upload_a.txt"]).run(timeout=30)
            self._multiselect_by_label(app, "Selecionar documentos para remover do índice").set_value(["doc-1"]).run(timeout=30)
            self._multiselect_by_label(app, "Documentos que o chat pode usar").set_value(["doc-1"]).run(timeout=30)
            self._multiselect_by_label(app, "Documentos para a análise estruturada").set_value(["doc-1"]).run(timeout=30)
            self._multiselect_by_label(
                app,
                "Combinações de provider/model para comparar",
            ).set_value(["ollama::fake-model-a", "ollama::fake-model-b"]).run(timeout=30)

            self._checkbox_by_label(app, "Comparar execução direta vs LangGraph (shadow)").set_value(True).run(timeout=30)
            self._checkbox_by_label(app, "Usar documentos selecionados").set_value(True).run(timeout=30)
            self._checkbox_by_label(app, "Usar documentos indexados na comparação").set_value(True).run(timeout=30)
            self._checkbox_by_label(app, "Permitir truncamento em embeddings").set_value(False).run(timeout=30)
            self._checkbox_by_label(app, "Show retrieval debug").set_value(True).run(timeout=30)

            if any(multiselect.label == "Documentos para grounding da comparação" for multiselect in app.multiselect):
                self._multiselect_by_label(app, "Documentos para grounding da comparação").set_value(["doc-1"]).run(timeout=30)

            self.assertEqual(len(app.exception), 0)

        for label, raw_values in selectbox_raw_value_matrix.items():
            with self.subTest(selectbox=label):
                with self._app_context(uploaded_files=uploaded_files) as (app, _temp_root, _mocks, _provider, _rag_settings):
                    for raw_value in raw_values:
                        self._selectbox_by_label(app, label).set_value(raw_value).run(timeout=30)
                        self.assertEqual(len(app.exception), 0)

    def test_structured_task_matrix_runs_all_tasks_and_both_strategies(self) -> None:
        document_backed_tasks = {"extraction", "summary", "checklist", "document_agent", "cv_analysis"}
        for task_name in ["extraction", "summary", "checklist", "document_agent", "cv_analysis", "code_analysis"]:
            for strategy_name in ["direct", "langgraph_context_retry"]:
                with self.subTest(task=task_name, strategy=strategy_name):
                    with self._app_context() as (app, _temp_root, _mocks, _provider, _rag_settings):
                        self._selectbox_by_label(app, "Task").set_value(task_name).run(timeout=30)
                        self._selectbox_by_label(app, "Estratégia de execução estruturada").set_value(strategy_name).run(timeout=30)
                        self._checkbox_by_label(app, "Usar documentos selecionados").set_value(task_name in document_backed_tasks).run(timeout=30)
                        self._text_area_by_label(
                            app,
                            "Input text (opcional quando usar documentos)",
                        ).set_value(f"Input de teste para {task_name}").run(timeout=30)
                        self._button_by_label(app, "Run structured analysis").click().run(timeout=30)

                        self.assertEqual(len(app.exception), 0)
                        stored = app.session_state.filtered_state.get("phase5_structured_result") or {}
                        self.assertEqual(stored.get("task_type"), task_name)
                        self.assertTrue(stored.get("success"))

    def test_model_comparison_and_deck_generation_work(self) -> None:
        with self._app_context() as (app, _temp_root, mocks, _provider, _rag_settings):
            self._text_area_by_label(app, "Prompt para comparar").set_value("Compare os dois modelos em bullets.").run(timeout=30)
            self._button_by_label(app, "Run model comparison").click().run(timeout=30)
            app.run(timeout=30)

            self.assertEqual(len(app.exception), 0)
            self.assertTrue(mocks.model_candidate.called)
            comparison_result = app.session_state.filtered_state.get("phase7_model_comparison_result")
            self.assertIsInstance(comparison_result, dict)
            self.assertEqual(len(comparison_result.get("candidate_results") or []), 2)

            self._button_by_label(app, "Generate Benchmark & Eval Executive Review Deck").click().run(timeout=30)
            stored_results = app.session_state.filtered_state.get("phase10_executive_deck_generation_result") or {}
            deck_result = stored_results.get(DEFAULT_PRESENTATION_EXPORT_KIND)
            self.assertIsInstance(deck_result, dict)
            self.assertEqual(deck_result.get("status"), "completed")
            self.assertTrue(mocks.deck_export.called)

    def test_history_buttons_and_document_mutation_controls_are_wired(self) -> None:
        with self._app_context(patch_document_mutations=True) as (app, temp_root, _mocks, _provider, _rag_settings):
            self._button_by_label(app, "Limpar histórico da Fase 5.5").click().run(timeout=30)
            self.assertFalse(get_phase55_shadow_log_path(temp_root).exists())

            self._button_by_label(app, "Limpar histórico direct vs LangGraph").click().run(timeout=30)
            self.assertFalse(get_phase55_langgraph_shadow_log_path(temp_root).exists())

            self._button_by_label(app, "Limpar histórico do agente documental").click().run(timeout=30)
            self.assertFalse(get_phase6_document_agent_log_path(temp_root).exists())

            self._button_by_label(app, "Limpar histórico de comparação da Fase 7").click().run(timeout=30)
            self.assertFalse(get_phase7_model_comparison_log_path(temp_root).exists())

        with self._app_context(patch_document_mutations=True) as (app, _temp_root, mocks, _provider, _rag_settings):
            self._multiselect_by_label(app, "Selecionar documentos para remover do índice").set_value(["doc-1"]).run(timeout=30)
            self._button_by_label(app, "Remover documentos selecionados").click().run(timeout=30)
            self.assertTrue(mocks.remove_documents.called)

        with self._app_context(patch_document_mutations=True) as (app, _temp_root, mocks, _provider, _rag_settings):
            self._button_by_label(app, "🗑️ Limpar índice").click().run(timeout=30)
            self.assertTrue(mocks.clear_index.called)

            self._button_by_label(app, "♻️ Reset físico Chroma").click().run(timeout=30)
            self.assertTrue(mocks.reset_chroma.called)

    def test_evidenceops_console_actions_work(self) -> None:
        with self._app_context() as (app, _temp_root, _mocks, _provider, _rag_settings):
            self._button_by_label(app, "Listar tools MCP").click().run(timeout=30)
            self._button_by_label(app, "Resumo do repositório").click().run(timeout=30)
            self._button_by_label(app, "Drift do repositório").click().run(timeout=30)
            self._button_by_label(app, "Listar ações abertas").click().run(timeout=30)
            self._button_by_label(app, "Planejar sync do corpus -> Nextcloud").click().run(timeout=30)
            self._button_by_label(app, "Planejar storylines -> Trello").click().run(timeout=30)
            self._button_by_label(app, "Planejar registro -> Notion").click().run(timeout=30)
            self._button_by_label(app, "Executar sync real -> Nextcloud").click().run(timeout=30)
            self._button_by_label(app, "Listar repositório remoto (Nextcloud)").click().run(timeout=30)
            self._text_input_by_label(app, "Buscar documentos via MCP").set_value("policy").run(timeout=30)
            self._button_by_label(app, "Executar busca documental via MCP").click().run(timeout=30)
            self._button_by_label(app, "Atualizar ação via MCP").click().run(timeout=30)

            self.assertEqual(len(app.exception), 0)
            console_state = app.session_state.filtered_state.get("phase95_evidenceops_mcp_console_state") or {}
            self.assertIn("tools", console_state)
            self.assertIn("repository_summary", console_state)
            self.assertIn("repository_drift", console_state)
            self.assertIn("open_actions", console_state)
            self.assertIn("nextcloud_plan", console_state)
            self.assertIn("trello_plan", console_state)
            self.assertIn("notion_plan", console_state)
            self.assertIn("nextcloud_sync_result", console_state)
            self.assertIn("nextcloud_remote_documents", console_state)
            self.assertIn("search_results", console_state)
            self.assertIn("updated_action", console_state)


if __name__ == "__main__":
    unittest.main()