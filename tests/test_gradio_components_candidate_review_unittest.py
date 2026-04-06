import unittest

from src.gradio_ui.components import build_result_summary_html, build_workflow_detail_html
from src.product.models import ProductWorkflowResult
from src.product.service import build_product_workflow_catalog
from src.structured.base import CVAnalysisPayload, ContactInfo
from src.structured.envelope import StructuredResult


class GradioComponentsCandidateReviewTests(unittest.TestCase):
    def test_build_workflow_detail_html_renders_phase_10_25_workflow_metadata(self) -> None:
        definition = build_product_workflow_catalog()["candidate_review"]

        html = build_workflow_detail_html(definition, selected_documents=1)

        self.assertIn("Candidate Review Deck", html)
        self.assertIn("Example prompts", html)
        self.assertIn("Expected outputs", html)
        self.assertIn("Workflow contract:", html)
        self.assertIn("docs/EXECUTIVE_DECK_GENERATION_CANDIDATE_REVIEW_DECK_CONTRACT_V1.md", html)
        self.assertIn("Add hiring context", html)

    def test_build_result_summary_html_renders_candidate_review_sections(self) -> None:
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
            status="warning",
            summary="Jane Doe is a strong applied AI profile.",
            recommendation="Keep the candidate in the active pipeline and run a targeted interview.",
            warnings=["Validate scale/production depth"],
            structured_result=StructuredResult(success=True, task_type="cv_analysis", validated_output=payload),
        )

        html = build_result_summary_html(result)

        self.assertIn("Candidate: Jane Doe", html)
        self.assertIn("Headline:", html)
        self.assertIn("Strengths", html)
        self.assertIn("Watchouts", html)
        self.assertIn("Next steps", html)
        self.assertIn("Strong applied AI execution", html)
        self.assertIn("Validate scale/production depth", html)
        self.assertIn("Recommendation:", html)

    def test_build_result_summary_html_escapes_candidate_review_content(self) -> None:
        payload = CVAnalysisPayload(
            task_type="cv_analysis",
            personal_info=ContactInfo(full_name="<Jane>", location="Remote"),
            skills=["Python"],
            languages=[],
            experience_entries=[],
            experience_years=0.0,
            strengths=["<script>alert('x')</script>"],
            improvement_areas=["Validate <ownership> examples"],
        )
        result = ProductWorkflowResult(
            workflow_id="candidate_review",
            workflow_label="Candidate Review",
            status="warning",
            summary="<b>Unsafe</b>",
            recommendation="Review <carefully>",
            warnings=["Validate <ownership> examples"],
            structured_result=StructuredResult(success=True, task_type="cv_analysis", validated_output=payload),
        )

        html = build_result_summary_html(result)

        self.assertIn("&lt;Jane&gt;", html)
        self.assertIn("&lt;script&gt;alert(&#x27;x&#x27;)&lt;/script&gt;", html)
        self.assertIn("Review &lt;carefully&gt;", html)
        self.assertNotIn("<script>", html)


if __name__ == "__main__":
    unittest.main()