import unittest

from src.product.models import ProductWorkflowResult
from src.product.presenters import build_policy_comparison_view, build_product_result_sections
from src.structured.base import CVAnalysisPayload, ComparisonFinding, ContactInfo, DocumentAgentPayload
from src.structured.envelope import StructuredResult


class ProductPresentersCandidateReviewTests(unittest.TestCase):
    def test_build_product_result_sections_enriches_candidate_review_output(self) -> None:
        payload = CVAnalysisPayload(
            task_type="cv_analysis",
            personal_info=ContactInfo(full_name="Jane Doe", location="São Paulo", email="jane@example.com"),
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


if __name__ == "__main__":
    unittest.main()