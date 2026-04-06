import unittest

from src.product.models import ProductWorkflowResult
from src.product.presenters import build_product_result_sections
from src.structured.base import CVAnalysisPayload, ContactInfo
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


if __name__ == "__main__":
    unittest.main()