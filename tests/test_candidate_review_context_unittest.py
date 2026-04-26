import unittest

from src.product.candidate_review_context import (
    build_candidate_review_input_text,
    normalize_role_brief_text,
    render_candidate_review_input_text,
)


class CandidateReviewContextTests(unittest.TestCase):
    def test_normalize_role_brief_extracts_key_sections(self) -> None:
        context = normalize_role_brief_text(
            """
            Role title: Senior ML Engineer
            Seniority: Senior
            Must-haves:
            - Python
            - MLOps
            Nice-to-have signals:
            - Marketplace experience
            Interview focus:
            - production incident handling
            - stakeholder communication
            Red flags:
            - no ownership examples
            """
        )

        self.assertEqual(context.title, "Senior ML Engineer")
        self.assertEqual(context.seniority, "Senior")
        self.assertEqual(context.must_haves[:2], ["Python", "MLOps"])
        self.assertIn("stakeholder communication", context.interview_focus)
        self.assertIn("no ownership examples", context.red_flags)

    def test_render_candidate_review_input_text_is_deterministic(self) -> None:
        context = normalize_role_brief_text(
            """
            Role title: Staff Backend Engineer
            Must-haves:
            - distributed systems
            - reliability
            """
        )
        text = render_candidate_review_input_text(context)

        self.assertIn("Evaluate the CV against the normalized hiring thesis below.", text)
        self.assertIn("Role title: Staff Backend Engineer", text)
        self.assertIn("- distributed systems", text)
        self.assertIn("preserve the existing candidate_review output style", text)

    def test_build_candidate_review_input_text_prefers_explicit_input(self) -> None:
        value = build_candidate_review_input_text(
            raw_role_brief_text="Role title: Senior ML Engineer",
            fallback_input_text="Use this explicit context instead.",
        )
        self.assertEqual(value, "Use this explicit context instead.")


if __name__ == "__main__":
    unittest.main()
