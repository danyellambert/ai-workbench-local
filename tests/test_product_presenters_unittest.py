import unittest

from src.product.action_plan_presenter import build_action_plan_view
from src.product.models import GroundingPreview, ProductArtifact, ProductWorkflowResult
from src.product.presenters import build_policy_comparison_view, build_product_result_sections
from src.structured.base import CVAnalysisPayload, ComparisonFinding, ContactInfo, DocumentAgentPayload
from src.structured.envelope import StructuredResult


class ProductPresentersCandidateReviewTests(unittest.TestCase):
    def test_build_product_result_sections_enriches_candidate_review_output(self) -> None:
        payload = CVAnalysisPayload(
            task_type="cv_analysis",
            personal_info=ContactInfo(full_name="Jane Doe", location="Sao Paulo", email="jane@example.com"),
            skills=["Python", "RAG", "Structured outputs"],
            languages=["English", "Portuguese"],
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
        result = ProductWorkflowResult(
            workflow_id="candidate_review",
            workflow_label="Candidate Review",
            summary="summary",
            recommendation="recommendation",
            structured_result=StructuredResult(success=True, task_type="cv_analysis", validated_output=payload),
        )

        sections = build_product_result_sections(result)

        self.assertEqual(sections["candidate_profile"]["name"], "Jane Doe")
        self.assertIn("Strong applied AI execution", sections["strengths"])
        self.assertIn("Validate scale/production depth", sections["watchouts"])
        self.assertTrue(sections["next_steps"])
        self.assertEqual(sections["tables"][0]["title"], "Evidence highlights")
        self.assertEqual(sections["tables"][1]["title"], "Experience highlights")

    def test_build_product_result_sections_sparse_candidate_keeps_fallback_evidence(self) -> None:
        payload = CVAnalysisPayload(
            task_type="cv_analysis",
            personal_info=ContactInfo(location="Remote"),
            skills=[],
            languages=[],
            education_entries=[],
            experience_entries=[],
            experience_years=0.0,
            strengths=[],
            improvement_areas=[],
        )
        result = ProductWorkflowResult(
            workflow_id="candidate_review",
            workflow_label="Candidate Review",
            summary="summary",
            recommendation="recommendation",
            structured_result=StructuredResult(success=True, task_type="cv_analysis", validated_output=payload),
        )

        sections = build_product_result_sections(result)

        self.assertEqual(sections["candidate_profile"]["name"], "Candidate")
        self.assertEqual(sections["tables"][0]["title"], "Evidence highlights")
        self.assertEqual(sections["tables"][0]["rows"][0][0], "Grounding status")


class ProductPresentersPolicyComparisonTests(unittest.TestCase):
    def test_build_policy_comparison_view_maps_grounded_differences_for_ui(self) -> None:
        payload = DocumentAgentPayload(
            task_type="document_agent",
            user_intent="document_comparison",
            answer_mode="comparison_structured",
            tool_used="compare_documents",
            summary="Policy B introduces stricter approval and governance controls than Policy A.",
            recommended_actions=[
                "Validate the approval gate delta with legal before rollout.",
                "Review liability and indemnification wording before signature.",
            ],
            compared_documents=["Policy A.pdf", "Policy B.pdf"],
            comparison_findings=[
                ComparisonFinding(
                    finding_type="obligation_change",
                    title="Formal approval became mandatory",
                    description="Policy B requires formal approval before onboarding while Policy A allows manager acknowledgment only.",
                    documents=["Policy A.pdf", "Policy B.pdf"],
                    evidence=[
                        "Policy A: manager acknowledgment is sufficient.",
                        "Policy B: formal approval is required before onboarding.",
                    ],
                )
            ],
            limitations=["Final legal review is still required before approval."],
            structured_response={
                "document_summaries": [
                    {
                        "document_id": "doc-a",
                        "label": "Policy A.pdf",
                        "summary": "Policy A allows onboarding with manager acknowledgment only.",
                        "key_points": ["Approval is lightweight in the current policy."],
                    },
                    {
                        "document_id": "doc-b",
                        "label": "Policy B.pdf",
                        "summary": "Policy B adds a formal approval requirement before onboarding.",
                        "key_points": ["Governance controls are stricter in the revised policy."],
                    },
                ]
            },
            confidence=0.81,
        )
        result = ProductWorkflowResult(
            workflow_id="policy_contract_comparison",
            workflow_label="Policy / Contract Comparison",
            status="warning",
            summary="Policy B introduces stricter approval and governance controls than Policy A.",
            recommendation="Use Policy B as the baseline and validate legal deltas before sign-off.",
            warnings=["A final legal review is still required before approval."],
            structured_result=StructuredResult(success=True, task_type="document_agent", validated_output=payload),
        )

        view = build_policy_comparison_view(result)

        self.assertEqual(view["executive_summary"]["counts"]["breaking"], 1)
        self.assertEqual(view["compared_documents"], ["Policy A.pdf", "Policy B.pdf"])
        self.assertTrue(view["must_fix_items"])
        self.assertEqual(view["must_fix_items"][0]["title"], "Formal approval became mandatory")
        self.assertTrue(view["differences"])
        self.assertEqual(view["differences"][0]["doc_a_label"], "Policy A.pdf")
        self.assertEqual(view["differences"][0]["doc_b_label"], "Policy B.pdf")
        self.assertIn("Validate the approval gate delta", view["negotiation_priorities"][0])
        self.assertEqual(view["recommendation"]["handoff"], "Legal / policy review")


class ProductPresentersActionPlanTests(unittest.TestCase):
    def test_build_action_plan_view_normalizes_grounded_actions_for_ui(self) -> None:
        payload = DocumentAgentPayload(
            task_type="document_agent",
            user_intent="action_plan_evidence_review",
            answer_mode="grounded_action_plan",
            tool_used="review_documents",
            summary="Vendor access remediation requires follow-up tasks before closure.",
            key_points=[
                "Three grounded remediation tasks were identified.",
                "Access-review evidence is incomplete for contractor offboarding.",
            ],
            limitations=["Awaiting final governance committee confirmation."],
            recommended_actions=[
                "Collect missing privileged-access approvals.",
                "Close temporary access exception before the next committee review.",
            ],
            structured_response={
                "extraction_payload": {
                    "task_type": "extraction",
                    "main_subject": "Vendor access remediation",
                    "risks": [
                        {
                            "description": "Temporary privileged access is still active for one contractor account.",
                            "impact": "Delayed remediation and unresolved access-control exposure.",
                            "owner": "Identity Ops",
                            "due_date": "2024-03-22",
                            "evidence": "Access Review Evidence Log still lists one contractor account with active elevated access.",
                        }
                    ],
                    "action_items": [
                        {
                            "description": "Collect missing privileged-access approvals.",
                            "owner": "Identity Ops",
                            "due_date": "2024-03-21",
                            "status": "in progress",
                            "evidence": "Approval email is missing for two privileged administrators.",
                        },
                        {
                            "description": "Close temporary access exception before the next committee review.",
                            "owner": "Security Governance",
                            "due_date": "2024-03-22",
                            "status": "blocked",
                            "evidence": "Temporary exception remains open pending governance committee approval.",
                        },
                        {
                            "description": "Document completed remediation closure note in the access review record.",
                            "owner": "Audit PMO",
                            "due_date": "2024-03-25",
                            "status": "done",
                            "evidence": "Closure note draft is prepared and ready for filing.",
                        },
                    ],
                    "missing_information": [
                        "Contractor offboarding evidence has not been attached to the current remediation record.",
                    ],
                }
            },
            sources=[
                {
                    "source": "Privileged Account Approval Email.pdf",
                    "document_id": "doc-1",
                    "chunk_id": 4,
                    "score": 0.93,
                    "snippet": "Approval email is missing for two privileged administrators.",
                },
                {
                    "source": "Access Review Evidence Log.pdf",
                    "document_id": "doc-2",
                    "chunk_id": 8,
                    "score": 0.89,
                    "snippet": "Access Review Evidence Log still lists one contractor account with active elevated access.",
                },
            ],
            confidence=0.84,
            needs_review=True,
            needs_review_reason="Governance sign-off is still pending for the temporary access exception.",
        )
        result = ProductWorkflowResult(
            workflow_id="action_plan_evidence_review",
            workflow_label="Action Plan / Evidence Review",
            status="warning",
            summary="Vendor access remediation: 3 actionable task(s) and 2 evidence gaps identified.",
            highlights=["Collect missing privileged-access approvals."],
            recommendation="Close the access-control evidence gaps before the next committee checkpoint.",
            structured_result=StructuredResult(success=True, task_type="document_agent", validated_output=payload),
            grounding_preview=GroundingPreview(
                strategy="document_scan",
                document_ids=["doc-1", "doc-2"],
                context_chars=864,
                source_block_count=2,
                preview_text="[Source: Approval Email] Missing privileged-access approval evidence remains open.",
            ),
            artifacts=[
                ProductArtifact(
                    artifact_type="contract_json",
                    label="Structured action-plan payload",
                    path="artifacts/action-plan.json",
                    download_name="action-plan.json",
                    available=True,
                )
            ],
            deck_export_kind="action_plan_deck",
            deck_available=True,
            warnings=["Awaiting final governance sign-off."],
            debug_metadata={
                "provider": "ollama",
                "model": "qwen2.5:7b",
                "context_strategy": "document_scan",
                "source_documents": ["doc-1", "doc-2"],
            },
        )

        view = build_action_plan_view(result)

        self.assertEqual(view["objective"], "Drive grounded follow-up actions for Vendor access remediation.")
        self.assertEqual(view["summary"]["total"], 3)
        self.assertEqual(view["summary"]["in_progress"], 1)
        self.assertEqual(view["summary"]["blocked"], 1)
        self.assertEqual(view["summary"]["done"], 1)
        self.assertEqual(view["document_ids"], ["doc-1", "doc-2"])
        self.assertEqual(view["items"][0]["owner"], "Identity Ops")
        self.assertEqual(view["items"][1]["status"], "blocked")
        self.assertEqual(view["critical_path"][0]["title"], "Close temporary access exception before the next committee review.")
        self.assertTrue(any(gap["status"] == "missing" for gap in view["evidence_gaps"]))
        self.assertTrue(any("contractor offboarding" in gap["detail"].lower() for gap in view["evidence_gaps"]))
        self.assertEqual(view["artifacts"][0]["artifact_type"], "contract_json")
        self.assertEqual(view["run_metadata"]["status"], "warning")
        self.assertEqual(view["run_metadata"]["provider"], "ollama")
        self.assertEqual(view["run_metadata"]["model"], "qwen2.5:7b")
        self.assertEqual(view["run_metadata"]["run_state"]["current_step"], "export")

    def test_build_action_plan_view_recovers_actions_from_grounding_preview_when_extraction_is_empty(self) -> None:
        payload = DocumentAgentPayload(
            task_type="document_agent",
            user_intent="action_plan_evidence_review",
            answer_mode="friendly",
            tool_used="extract_operational_tasks",
            summary="Governance Committee Minutes and Action Items: 0 actionable task(s), 0 deadline(s) and 0 operational risk(s) identified.",
            recommended_actions=[
                "Open the cited source excerpts to confirm the interpretation before acting.",
                "Forward the result for human review before making a final decision.",
            ],
            structured_response={
                "actions": [],
                "extraction_payload": {
                    "task_type": "extraction",
                    "main_subject": "Governance Committee Minutes and Action Items",
                    "action_items": [],
                    "risks": [],
                    "missing_information": [],
                },
            },
            sources=[
                {
                    "source": "Governance Committee Minutes and Action Items.pdf",
                    "document_id": "doc-minutes",
                    "chunk_id": 1,
                    "score": 0.94,
                    "snippet": "Negotiate liability cap with vendor legal Maria Santos 2024-03-22 In progress CTR-010 Section 7.3",
                },
                {
                    "source": "Nonconformance Report - Vendor Access Review.pdf",
                    "document_id": "doc-ncr",
                    "chunk_id": 2,
                    "score": 0.91,
                    "snippet": "Reconstruct access-review evidence and obtain system-owner sign-off Priya Nair 2024-03-18 In progress",
                },
            ],
            confidence=0.67,
            needs_review=True,
            needs_review_reason="operational_extraction_without_grounded_actions",
        )
        result = ProductWorkflowResult(
            workflow_id="action_plan_evidence_review",
            workflow_label="Action Plan / Evidence Review",
            status="warning",
            summary="Governance Committee Minutes and Action Items: 0 actionable task(s), 0 deadline(s) and 0 operational risk(s) identified.",
            recommendation="Open the cited source excerpts to confirm the interpretation before acting.",
            structured_result=StructuredResult(success=True, task_type="document_agent", validated_output=payload),
            grounding_preview=GroundingPreview(
                strategy="document_scan",
                document_ids=["doc-minutes", "doc-ncr"],
                context_chars=2048,
                source_block_count=2,
                preview_text=(
                    "[Source: Governance Committee Minutes and Action Items.pdf] Action Register Action Item Owner Due Date Status Evidence / Source "
                    "Negotiate liability cap with vendor legal Maria Santos 2024-03-22 In progress CTR-010 Section 7.3 unlimited liability clause "
                    "Draft SCC Appendix for data residency James Park 2024-03-25 Open CTR-013 transfer mechanism gap / GOV-001 "
                    "Set up auto-renewal calendar alerts Operations 2024-03-18 In progress CTR-010 Section 8.2 90-day notice risk "
                    "Next committee checkpoint scheduled for 2024-03-27. "
                    "[Source: Nonconformance Report - Vendor Access Review.pdf] 3. Corrective Actions Action Owner Due Date Status "
                    "Reconstruct access-review evidence and obtain system-owner sign-off Priya Nair 2024-03-18 In progress "
                    "Negotiate liability cap with vendor legal Maria Santos 2024-03-22 In progress "
                    "Draft SCC Appendix C and transfer rationale memo James Park 2024-03-25 Open "
                    "Define explicit incident response SLOs in policy and contract package Alex Rivera 2024-03-28 Open 4. Closure Criteria"
                ),
            ),
            deck_export_kind="action_plan_deck",
            deck_available=True,
            warnings=["operational_extraction_without_grounded_actions"],
            debug_metadata={"provider": "ollama", "model": "nemotron-3-nano:30b-cloud"},
        )

        view = build_action_plan_view(result)

        titles = [item["title"] for item in view["items"]]
        self.assertIn("Negotiate liability cap with vendor legal", titles)
        self.assertIn("Reconstruct access-review evidence and obtain system-owner sign-off", titles)
        self.assertIn("Define explicit incident response SLOs in policy and contract package", titles)
        owners = {item["title"]: item["owner"] for item in view["items"]}
        self.assertEqual(owners["Negotiate liability cap with vendor legal"], "Maria Santos")
        self.assertEqual(owners["Reconstruct access-review evidence and obtain system-owner sign-off"], "Priya Nair")
        due_dates = {item["title"]: item["due_date"] for item in view["items"]}
        self.assertEqual(due_dates["Draft SCC Appendix C and transfer rationale memo"], "2024-03-25")
        self.assertGreaterEqual(view["summary"]["total"], 4)
        self.assertGreaterEqual(view["summary"]["critical_path"], 1)


if __name__ == "__main__":
    unittest.main()
