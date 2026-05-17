import unittest

from src.product.candidate_review_presenter import build_candidate_review_view
from src.product.models import GroundingPreview, ProductWorkflowResult
from src.structured.base import CVAnalysisPayload, ContactInfo, ExperienceEntry
from src.structured.envelope import StructuredResult


class CandidateReviewPresenterTests(unittest.TestCase):
    def test_build_candidate_review_view_includes_role_context_and_document_metrics(self) -> None:
        payload = CVAnalysisPayload(
            personal_info=ContactInfo(full_name="Ada Candidate", location="Remote"),
            skills=["Python", "Distributed systems", "MLOps"],
            strengths=["Strong ownership", "Clear delivery history"],
            improvement_areas=["Needs deeper stakeholder examples"],
            experience_years=7.0,
            experience_entries=[
                ExperienceEntry(
                    title="Senior Engineer",
                    organization="Acme",
                    date_range="2019-2026",
                    bullets=["Led backend platform migration", "Owned production reliability improvements"],
                )
            ],
        )
        result = ProductWorkflowResult(
            workflow_id="candidate_review",
            workflow_label="Candidate Review",
            status="completed",
            summary="Ada Candidate currently reads as a senior hiring profile.",
            recommendation="Advance the candidate to the next stage with focused validation of leadership, scope and business impact.",
            structured_result=StructuredResult(success=True, task_type="cv_analysis", validated_output=payload),
            grounding_preview=GroundingPreview(
                strategy="document_scan",
                document_ids=["cv-1"],
                context_chars=900,
                source_block_count=0,
                preview_text="Candidate grounding preview without explicit source markers",
            ),
            highlights=["Strong ownership"],
            warnings=[],
            debug_metadata={
                "input_text": """
                Role title: Staff Platform Engineer
                Target seniority: Staff
                Must-have requirements:
                - distributed systems
                - reliability
                Interview focus:
                - architecture trade-offs
                """,
            },
        )

        view = build_candidate_review_view(result)

        self.assertEqual(view["candidate_profile"]["name"], "Ada Candidate")
        self.assertEqual(view["role_context"]["title"], "Staff Platform Engineer")
        self.assertEqual(view["document_metrics"]["source_block_count"], 0)
        self.assertFalse(view["document_metrics"]["show_source_block_count"])
        self.assertTrue(view["strengths"])
        self.assertTrue(view["next_steps"])


if __name__ == "__main__":
    unittest.main()
