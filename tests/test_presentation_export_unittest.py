import unittest

from src.services.presentation_export import (
    ACTION_PLAN_EXPORT_KIND,
    BENCHMARK_EVAL_EXECUTIVE_REVIEW_PRODUCT_EXPORT_KIND,
    CANDIDATE_REVIEW_EXPORT_KIND,
    DEFAULT_PRESENTATION_EXPORT_CONTRACT_VERSION,
    DEFAULT_PRESENTATION_EXPORT_KIND,
    DOCUMENT_REVIEW_EXPORT_KIND,
    EVIDENCE_PACK_EXPORT_KIND,
    POLICY_CONTRACT_COMPARISON_EXPORT_KIND,
    build_action_plan_deck_contract,
    build_benchmark_eval_contract_from_logs,
    build_candidate_review_deck_contract,
    build_document_review_deck_contract,
    build_evidence_pack_deck_contract,
    build_policy_contract_comparison_deck_contract,
    build_ppt_creator_payload_from_benchmark_eval_contract,
    build_ppt_creator_payload_from_executive_deck_contract,
    normalize_executive_deck_export_kind,
)
from src.structured.base import (
    AgentSource,
    CVAnalysisPayload,
    ComparisonFinding,
    ContactInfo,
    DocumentAgentPayload,
)
from src.structured.envelope import StructuredResult

class PresentationExportTests(unittest.TestCase):
    def _sample_model_comparison_entries(self) -> list[dict[str, object]]:
        return [
            {
                "benchmark_use_case": "executive_summary",
                "prompt_profile": "neutral",
                "response_format": "bullet_list",
                "retrieval_strategy": "manual_hybrid",
                "embedding_provider": "ollama",
                "embedding_model": "embeddinggemma:300m",
                "use_documents": True,
                "aggregate": {
                    "total_candidates": 2,
                    "success_rate": 1.0,
                    "avg_latency_s": 0.95,
                    "avg_output_chars": 80.0,
                    "avg_format_adherence": 0.95,
                    "avg_groundedness_score": 0.74,
                    "avg_schema_adherence": 0.0,
                    "avg_use_case_fit_score": 0.89,
                },
                "candidate_results": [
                    {
                        "provider_effective": "ollama",
                        "model_effective": "qwen2.5:7b",
                        "runtime_bucket": "local",
                        "quantization_family": "unspecified_local",
                        "success": True,
                        "latency_s": 1.1,
                        "output_chars": 120,
                        "format_adherence": 1.0,
                        "groundedness_score": 0.8,
                        "use_case_fit_score": 0.9,
                    },
                    {
                        "provider_effective": "openai",
                        "model_effective": "gpt-4o-mini",
                        "runtime_bucket": "cloud",
                        "quantization_family": "cloud_managed",
                        "success": True,
                        "latency_s": 0.8,
                        "output_chars": 100,
                        "format_adherence": 0.9,
                        "groundedness_score": 0.68,
                        "use_case_fit_score": 0.88,
                    },
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
            },
            {
                "suite_name": "checklist_regression",
                "task_type": "checklist",
                "case_name": "fixture:checklist",
                "provider": "ollama",
                "model": "qwen2.5:7b",
                "status": "WARN",
                "score": 8,
                "max_score": 10,
                "latency_s": 2.4,
                "needs_review": True,
            },
        ]

    def _sample_document_agent_result(self) -> StructuredResult:
        payload = DocumentAgentPayload(
            task_type="document_agent",
            agent_label="Document Operations Copilot",
            user_intent="policy_review",
            intent_reason="Document asks for a grounded compliance review.",
            answer_mode="review",
            tool_used="policy_compliance",
            summary="The policy adds new obligations and still depends on final legal validation.",
            key_points=[
                "New formal approval obligation.",
                "The owner for the annual control has not yet been defined.",
            ],
            limitations=["Final legal validation is still pending."],
            recommended_actions=["Define the control owner.", "Review critical clauses with legal."],
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
                "actions": ["Define the annual control owner"],
                "extraction_payload": {
                    "risks": [
                        {
                            "description": "Owner not defined for the annual control",
                            "owner": "Compliance",
                            "due_date": "2026-04-10",
                            "evidence": "Page 12",
                        }
                    ],
                    "action_items": [
                        {
                            "description": "Define the annual control owner",
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
        return StructuredResult(
            success=True,
            task_type="document_agent",
            validated_output=payload,
            source_documents=["policy_2026"],
        )

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
        return StructuredResult(
            success=True,
            task_type="cv_analysis",
            validated_output=payload,
            source_documents=["cv_jane_doe"],
        )

    def test_build_benchmark_eval_contract_from_logs_creates_concrete_contract(self) -> None:
        contract = build_benchmark_eval_contract_from_logs(
            model_comparison_entries=self._sample_model_comparison_entries(),
            eval_entries=self._sample_eval_entries(),
        )

        self.assertEqual(contract.contract_version, DEFAULT_PRESENTATION_EXPORT_CONTRACT_VERSION)
        self.assertEqual(contract.export_kind, DEFAULT_PRESENTATION_EXPORT_KIND)
        self.assertEqual(contract.presentation.theme, "executive_premium_minimal")
        self.assertEqual(contract.model_comparison_snapshot.total_candidates, 2)
        self.assertEqual(contract.model_comparison_snapshot.top_model, "qwen2.5:7b")
        self.assertEqual(contract.eval_snapshot.total_runs, 2)
        self.assertEqual(contract.eval_snapshot.top_suite_name, "structured_smoke_eval")
        self.assertGreaterEqual(len(contract.key_metrics), 3)
        self.assertTrue(any("qwen2.5:7b" in item for item in contract.key_highlights))
        self.assertEqual(contract.model_leaderboard[0].model, "qwen2.5:7b")
        self.assertEqual(contract.eval_suite_leaderboard[0].suite_name, "structured_smoke_eval")
        self.assertIn("phase7_model_comparison_log", contract.data_sources)
        self.assertIn("phase8_eval_store", contract.data_sources)

    def test_build_ppt_creator_payload_from_contract_generates_expected_slide_sequence(self) -> None:
        contract = build_benchmark_eval_contract_from_logs(
            model_comparison_entries=self._sample_model_comparison_entries(),
            eval_entries=self._sample_eval_entries(),
        )

        payload = build_ppt_creator_payload_from_benchmark_eval_contract(contract)

        self.assertEqual(payload["presentation"]["title"], contract.presentation.title)
        slide_types = [slide["type"] for slide in payload["slides"]]
        self.assertEqual(slide_types[0], "title")
        self.assertIn("summary", slide_types)
        self.assertIn("metrics", slide_types)
        self.assertIn("two_column", slide_types)
        self.assertIn("bullets", slide_types)
        self.assertEqual(slide_types.count("table"), 2)

        model_table = next(slide for slide in payload["slides"] if slide.get("title") == "Model leaderboard")
        self.assertEqual(model_table["table_columns"], ["Model", "Signal", "Latency (s)", "Fit"])
        self.assertEqual(model_table["table_rows"][0][0], "qwen2.5:7b")

        comparison_slide = next(slide for slide in payload["slides"] if slide["type"] == "two_column")
        self.assertEqual(len(comparison_slide["two_column_columns"]), 2)
        self.assertEqual(comparison_slide["two_column_columns"][0]["title"], "Recommendation")
        self.assertEqual(comparison_slide["two_column_columns"][1]["title"], "Watchouts")

    def test_build_document_review_and_comparison_decks_from_document_agent(self) -> None:
        structured_result = self._sample_document_agent_result()

        document_review = build_document_review_deck_contract(structured_result=structured_result)
        self.assertEqual(document_review.export_kind, DOCUMENT_REVIEW_EXPORT_KIND)
        self.assertTrue(document_review.tables)
        self.assertTrue(document_review.recommendation)

        comparison_review = build_policy_contract_comparison_deck_contract(structured_result=structured_result)
        self.assertEqual(comparison_review.export_kind, POLICY_CONTRACT_COMPARISON_EXPORT_KIND)
        self.assertTrue(comparison_review.tables)

        payload = build_ppt_creator_payload_from_executive_deck_contract(comparison_review)
        slide_types = [slide["type"] for slide in payload["slides"]]
        self.assertEqual(slide_types[0], "title")
        self.assertIn("summary", slide_types)
        self.assertIn("two_column", slide_types)

    def test_build_action_candidate_and_evidence_pack_decks(self) -> None:
        candidate_review = build_candidate_review_deck_contract(structured_result=self._sample_cv_analysis_result())
        self.assertEqual(candidate_review.export_kind, CANDIDATE_REVIEW_EXPORT_KIND)
        self.assertIn("Jane Doe", candidate_review.presentation.title)
        self.assertEqual(candidate_review.candidate_profile["name"], "Jane Doe")
        self.assertTrue(candidate_review.strengths)
        self.assertTrue(candidate_review.gaps)
        self.assertTrue(candidate_review.evidence_highlights)
        candidate_payload = build_ppt_creator_payload_from_executive_deck_contract(candidate_review)
        candidate_slide_titles = [slide.get("title") for slide in candidate_payload["slides"]]
        self.assertIn("Evidence highlights", candidate_slide_titles)
        self.assertIn("Gaps vs hiring thesis", candidate_slide_titles)

        action_plan = build_action_plan_deck_contract(
            evidenceops_action_entries=[
                {
                    "action_type": "recommended_action",
                    "description": "Define the annual control owner",
                    "owner": "Compliance",
                    "due_date": "2026-04-10",
                    "status": "open",
                    "review_type": "risk_gap_review",
                }
            ]
        )
        self.assertEqual(action_plan.export_kind, ACTION_PLAN_EXPORT_KIND)
        self.assertTrue(action_plan.tables)

        evidence_pack = build_evidence_pack_deck_contract(
            evidenceops_worklog_entries=[
                {
                    "review_type": "risk_gap_review",
                    "summary": "EvidenceOps found findings and open actions.",
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
                            "description": "Update evidence register",
                            "owner": "Compliance",
                            "due_date": "2026-04-12",
                            "status": "open",
                        }
                    ],
                    "recommended_actions": ["Update evidence register"],
                    "limitations": ["One piece of evidence still depends on manual validation"],
                }
            ],
            evidenceops_action_entries=[
                {
                    "action_type": "recommended_action",
                    "description": "Update evidence register",
                    "owner": "Compliance",
                    "due_date": "2026-04-12",
                    "status": "open",
                }
            ],
        )
        self.assertEqual(evidence_pack.export_kind, EVIDENCE_PACK_EXPORT_KIND)
        self.assertTrue(evidence_pack.tables)
        payload = build_ppt_creator_payload_from_executive_deck_contract(evidence_pack)
        self.assertEqual(payload["slides"][0]["type"], "title")

    def test_build_candidate_review_deck_contract_handles_sparse_cv_with_fallbacks(self) -> None:
        sparse_result = StructuredResult(
            success=True,
            task_type="cv_analysis",
            validated_output=CVAnalysisPayload(
                task_type="cv_analysis",
                personal_info=ContactInfo(location="Remote"),
                skills=[],
                languages=[],
                education_entries=[],
                experience_entries=[],
                experience_years=0.0,
                strengths=[],
                improvement_areas=[],
            ),
            source_documents=["cv_sparse"],
        )

        contract = build_candidate_review_deck_contract(structured_result=sparse_result)

        self.assertEqual(contract.candidate_profile["name"], "Candidate")
        self.assertEqual(contract.candidate_profile["location"], "Remote")
        self.assertTrue(contract.evidence_highlights)
        self.assertEqual(contract.evidence_highlights[0].label, "Grounding status")
        self.assertTrue(contract.gaps)
        self.assertTrue(contract.next_steps)
        self.assertIn("Hold before advancing", contract.recommendation or "")
        self.assertIn("Primary watchout", contract.executive_summary)
        sparse_payload = build_ppt_creator_payload_from_executive_deck_contract(contract)
        sparse_slide_titles = [slide.get("title") for slide in sparse_payload["slides"]]
        self.assertIn("Evidence highlights", sparse_slide_titles)

    def test_normalize_executive_deck_export_kind_accepts_product_alias(self) -> None:
        self.assertEqual(
            normalize_executive_deck_export_kind(BENCHMARK_EVAL_EXECUTIVE_REVIEW_PRODUCT_EXPORT_KIND),
            DEFAULT_PRESENTATION_EXPORT_KIND,
        )
