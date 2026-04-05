import json
import tempfile
import unittest
from pathlib import Path
from urllib import error as urllib_error
from urllib.parse import parse_qs, urlparse
from unittest.mock import patch

from src.config import PresentationExportSettings
from src.services.presentation_export import (
    ACTION_PLAN_EXPORT_KIND,
    BENCHMARK_EVAL_EXECUTIVE_REVIEW_PRODUCT_EXPORT_KIND,
    CANDIDATE_REVIEW_EXPORT_KIND,
    DEFAULT_PRESENTATION_EXPORT_KIND,
    DOCUMENT_REVIEW_EXPORT_KIND,
    EVIDENCE_PACK_EXPORT_KIND,
    POLICY_CONTRACT_COMPARISON_EXPORT_KIND,
)
from src.services.presentation_export_service import generate_benchmark_eval_executive_review_deck, generate_executive_deck
from src.structured.base import AgentSource, CVAnalysisPayload, ComparisonFinding, ContactInfo, DocumentAgentPayload
from src.structured.envelope import StructuredResult


class _FakeHttpResponse:
    def __init__(self, body: bytes, status: int = 200) -> None:
        self._body = body
        self.status = status

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> "_FakeHttpResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False


class PresentationExportServiceTests(unittest.TestCase):
    def _sample_model_comparison_entries(self) -> list[dict[str, object]]:
        return [
            {
                "benchmark_use_case": "executive_summary",
                "prompt_profile": "neutro",
                "response_format": "bullet_list",
                "retrieval_strategy": "manual_hybrid",
                "embedding_provider": "ollama",
                "embedding_model": "embeddinggemma:300m",
                "use_documents": True,
                "aggregate": {
                    "total_candidates": 2,
                    "success_rate": 1.0,
                    "avg_latency_s": 0.95,
                    "avg_format_adherence": 0.95,
                    "avg_use_case_fit_score": 0.89,
                },
                "candidate_results": [
                    {
                        "provider_effective": "ollama",
                        "model_effective": "qwen2.5:7b",
                        "runtime_bucket": "local",
                        "success": True,
                        "latency_s": 1.1,
                        "format_adherence": 1.0,
                        "use_case_fit_score": 0.9,
                    }
                ],
            }
        ]

    def _sample_eval_entries(self) -> list[dict[str, object]]:
        return [
            {
                "suite_name": "structured_smoke_eval",
                "task_type": "summary",
                "case_name": "fixture:summary",
                "provider": "ollama",
                "model": "qwen2.5:7b",
                "status": "PASS",
                "score": 5,
                "max_score": 5,
                "latency_s": 1.2,
                "needs_review": False,
            }
        ]

    def _sample_document_agent_result(self) -> StructuredResult:
        payload = DocumentAgentPayload(
            task_type="document_agent",
            agent_label="Document Operations Copilot",
            user_intent="policy_review",
            intent_reason="Grounded policy review requested.",
            answer_mode="review",
            tool_used="policy_compliance",
            summary="A política adiciona obrigações novas e ainda depende de validação jurídica final.",
            key_points=["Nova obrigação de aprovação formal.", "Owner do controle anual ainda não foi definido."],
            limitations=["Validação jurídica final ainda pendente."],
            recommended_actions=["Definir owner do controle.", "Revisar cláusulas críticas com jurídico."],
            guardrails_applied=["Human review required for final policy decision."],
            available_tools=[],
            compared_documents=["Policy 2025", "Policy 2026"],
            comparison_findings=[
                ComparisonFinding(
                    finding_type="obligation_change",
                    title="Formal approval became mandatory",
                    description="The 2026 version requires formal approval for supplier onboarding.",
                    documents=["Policy 2025", "Policy 2026"],
                    evidence=["Page 4 - approval formal required"],
                )
            ],
            checklist_preview=["Define owner", "Validate legal sign-off"],
            structured_response={
                "review_type": "policy_compliance",
                "gaps": ["Legal sign-off still missing"],
                "actions": ["Define owner do controle anual"],
                "extraction_payload": {
                    "risks": [
                        {
                            "description": "Owner não definido para o controle anual",
                            "owner": "Compliance",
                            "due_date": "2026-04-10",
                            "evidence": "Page 12",
                        }
                    ],
                    "action_items": [
                        {
                            "description": "Definir owner do controle anual",
                            "owner": "Compliance",
                            "due_date": "2026-04-10",
                            "status": "open",
                        }
                    ],
                    "missing_information": ["Legal sign-off still missing"],
                },
            },
            sources=[
                AgentSource(
                    source="Policy_2026.pdf",
                    document_id="policy_2026",
                    snippet="Formal approval is required for supplier onboarding.",
                )
            ],
            tool_runs=[],
            confidence=0.82,
            needs_review=True,
            needs_review_reason="legal_signoff_missing",
        )
        return StructuredResult(success=True, task_type="document_agent", validated_output=payload, source_documents=["policy_2026"])

    def _sample_cv_analysis_result(self) -> StructuredResult:
        payload = CVAnalysisPayload(
            task_type="cv_analysis",
            personal_info=ContactInfo(full_name="Jane Doe", location="São Paulo", email="jane@example.com"),
            skills=["Python", "RAG", "Structured outputs"],
            languages=["English", "Portuguese"],
            education_entries=[
                {
                    "degree": "BSc Computer Science",
                    "institution": "USP",
                    "date_range": "2018-2022",
                    "location": "São Paulo",
                }
            ],
            experience_entries=[
                {
                    "title": "Applied AI Engineer",
                    "organization": "Acme",
                    "date_range": "2022-2025",
                    "bullets": ["Built RAG pipelines", "Shipped eval-driven AI features"],
                }
            ],
            experience_years=3.5,
            strengths=["Strong applied AI execution", "Good product + engineering bridge"],
            improvement_areas=["Validate scale/production depth"],
        )
        return StructuredResult(success=True, task_type="cv_analysis", validated_output=payload, source_documents=["cv_jane_doe"])

    def _service_settings(self, root: str) -> PresentationExportSettings:
        return PresentationExportSettings(
            enabled=True,
            base_url="http://deck.local",
            timeout_seconds=15,
            remote_output_dir="outputs/ai_workbench_exports",
            remote_preview_dir="outputs/ai_workbench_export_previews",
            local_artifact_dir=Path(root) / "artifacts",
            include_review=True,
            preview_backend="auto",
            require_real_previews=False,
            fail_on_regression=False,
        )

    def _fake_urlopen(self, request, timeout=0):
        url = request.full_url if hasattr(request, "full_url") else str(request)
        parsed = urlparse(url)
        if parsed.path == "/health":
            return _FakeHttpResponse(json.dumps({"status": "ok"}).encode("utf-8"))
        if parsed.path == "/render":
            body = {
                "result": {
                    "output_path": "outputs/ai_workbench_exports/export/deck.pptx",
                    "quality_review": {"score": 0.91},
                    "preview_result": {
                        "preview_manifest": "outputs/ai_workbench_export_previews/export/preview-manifest.json",
                        "thumbnail_sheet": "outputs/ai_workbench_export_previews/export/thumbnails.png",
                    },
                }
            }
            return _FakeHttpResponse(json.dumps(body).encode("utf-8"))
        if parsed.path == "/artifact":
            remote_path = parse_qs(parsed.query).get("path", [""])[0]
            if remote_path.endswith("deck.pptx"):
                return _FakeHttpResponse(b"pptx-binary")
            if remote_path.endswith("preview-manifest.json"):
                return _FakeHttpResponse(b'{"preview_count": 1}')
            if remote_path.endswith("thumbnails.png"):
                return _FakeHttpResponse(b"png-binary")
        raise AssertionError(f"Unexpected request URL: {url}")

    def test_generate_benchmark_eval_executive_review_deck_persists_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = self._service_settings(temp_dir)

            with patch("src.services.presentation_export_service.urllib_request.urlopen", side_effect=self._fake_urlopen):
                result = generate_benchmark_eval_executive_review_deck(
                    model_comparison_entries=self._sample_model_comparison_entries(),
                    eval_entries=self._sample_eval_entries(),
                    settings=settings,
                )

            self.assertEqual(result["status"], "completed")
            self.assertTrue(Path(result["local_contract_path"]).exists())
            self.assertTrue(Path(result["local_payload_path"]).exists())
            self.assertTrue(Path(result["local_render_response_path"]).exists())
            self.assertTrue(Path(result["local_pptx_path"]).exists())
            self.assertTrue(Path(result["local_review_path"]).exists())
            self.assertTrue(Path(result["local_preview_manifest_path"]).exists())
            self.assertTrue(Path(result["local_thumbnail_sheet_path"]).exists())

    def test_generate_benchmark_eval_executive_review_deck_handles_healthcheck_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = self._service_settings(temp_dir)

            with patch(
                "src.services.presentation_export_service.urllib_request.urlopen",
                side_effect=urllib_error.URLError("offline"),
            ):
                result = generate_benchmark_eval_executive_review_deck(
                    model_comparison_entries=self._sample_model_comparison_entries(),
                    eval_entries=self._sample_eval_entries(),
                    settings=settings,
                )

            self.assertEqual(result["status"], "service_unavailable")
            self.assertTrue(Path(result["local_contract_path"]).exists())
            self.assertTrue(Path(result["local_payload_path"]).exists())
            self.assertIsNone(result["local_pptx_path"])

    def test_generate_executive_deck_supports_all_non_p1_export_kinds(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            settings = self._service_settings(temp_dir)
            test_cases = [
                (DOCUMENT_REVIEW_EXPORT_KIND, {"structured_result": self._sample_document_agent_result()}),
                (POLICY_CONTRACT_COMPARISON_EXPORT_KIND, {"structured_result": self._sample_document_agent_result()}),
                (
                    ACTION_PLAN_EXPORT_KIND,
                    {
                        "evidenceops_action_entries": [
                            {
                                "action_type": "recommended_action",
                                "description": "Definir owner do controle anual",
                                "owner": "Compliance",
                                "due_date": "2026-04-10",
                                "status": "open",
                            }
                        ]
                    },
                ),
                (CANDIDATE_REVIEW_EXPORT_KIND, {"structured_result": self._sample_cv_analysis_result()}),
                (
                    EVIDENCE_PACK_EXPORT_KIND,
                    {
                        "evidenceops_worklog_entries": [
                            {
                                "review_type": "risk_gap_review",
                                "summary": "EvidenceOps encontrou findings e ações abertas.",
                                "workflow_id": "wf_123",
                                "findings": [
                                    {
                                        "finding_type": "risk",
                                        "title": "Missing annual control evidence",
                                        "description": "Annual control evidence is missing",
                                        "evidence": ["Doc A / page 4"],
                                    }
                                ],
                                "action_items": [
                                    {
                                        "action_type": "recommended_action",
                                        "description": "Atualizar evidence register",
                                        "owner": "Compliance",
                                        "due_date": "2026-04-12",
                                        "status": "open",
                                    }
                                ],
                                "recommended_actions": ["Atualizar evidence register"],
                            }
                        ],
                        "evidenceops_action_entries": [
                            {
                                "action_type": "recommended_action",
                                "description": "Atualizar evidence register",
                                "owner": "Compliance",
                                "due_date": "2026-04-12",
                                "status": "open",
                            }
                        ],
                    },
                ),
            ]

            with patch("src.services.presentation_export_service.urllib_request.urlopen", side_effect=self._fake_urlopen):
                for export_kind, kwargs in test_cases:
                    with self.subTest(export_kind=export_kind):
                        result = generate_executive_deck(export_kind=export_kind, settings=settings, **kwargs)
                        self.assertEqual(result["status"], "completed")
                        self.assertEqual(result["export_kind"], export_kind)
                        self.assertTrue(Path(result["local_contract_path"]).exists())
                        self.assertTrue(Path(result["local_payload_path"]).exists())
                        self.assertTrue(Path(result["local_pptx_path"]).exists())

    def test_generate_executive_deck_accepts_product_alias_and_feature_flags_by_export_kind(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            enabled_settings = self._service_settings(temp_dir)
            disabled_settings = PresentationExportSettings(
                enabled=True,
                base_url="http://deck.local",
                timeout_seconds=15,
                remote_output_dir="outputs/ai_workbench_exports",
                remote_preview_dir="outputs/ai_workbench_export_previews",
                local_artifact_dir=Path(temp_dir) / "artifacts_disabled",
                include_review=True,
                preview_backend="auto",
                require_real_previews=False,
                fail_on_regression=False,
                enabled_export_kinds=(DEFAULT_PRESENTATION_EXPORT_KIND,),
            )

            with patch("src.services.presentation_export_service.urllib_request.urlopen", side_effect=self._fake_urlopen):
                aliased_result = generate_executive_deck(
                    export_kind=BENCHMARK_EVAL_EXECUTIVE_REVIEW_PRODUCT_EXPORT_KIND,
                    model_comparison_entries=self._sample_model_comparison_entries(),
                    eval_entries=self._sample_eval_entries(),
                    settings=enabled_settings,
                )
            self.assertEqual(aliased_result["status"], "completed")
            self.assertEqual(aliased_result["export_kind"], DEFAULT_PRESENTATION_EXPORT_KIND)

            disabled_result = generate_executive_deck(
                export_kind=DOCUMENT_REVIEW_EXPORT_KIND,
                structured_result=self._sample_document_agent_result(),
                settings=disabled_settings,
            )
            self.assertEqual(disabled_result["status"], "disabled_export_kind")
            self.assertIn(DEFAULT_PRESENTATION_EXPORT_KIND, disabled_result["error_message"])


if __name__ == "__main__":
    unittest.main()