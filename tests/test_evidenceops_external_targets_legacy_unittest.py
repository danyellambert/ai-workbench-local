import unittest
from unittest.mock import patch
import os

from src.config import get_evidenceops_external_settings
from src.services.evidenceops_external_targets import (
    build_external_targets_status,
    build_notion_storyline_register_entries,
    build_phase95_corpus_mapping,
    list_nextcloud_repository_documents,
    build_trello_storyline_cards,
    sync_phase95_corpus_to_nextcloud,
)
from src.services.evidenceops_local_ops import list_evidenceops_repository_entries


class Phase95ExternalTargetsTests(unittest.TestCase):
    def test_external_settings_default_to_option_b_primary_corpus(self) -> None:
        with patch.dict(
            os.environ,
            {
                "EVIDENCEOPS_EXTERNAL_SYNC_ENABLED": "false",
                "EVIDENCEOPS_REPOSITORY_BACKEND": "local",
                "EVIDENCEOPS_NEXTCLOUD_BASE_URL": "",
                "EVIDENCEOPS_NEXTCLOUD_USERNAME": "",
                "EVIDENCEOPS_NEXTCLOUD_APP_PASSWORD": "",
            },
            clear=False,
        ):
            settings = get_evidenceops_external_settings()
            self.assertEqual(settings.repository_backend, "local")
            self.assertTrue(str(settings.corpus_primary_root).endswith("data/corpus_revisado/option_b_synthetic_premium"))
            self.assertTrue(str(settings.corpus_public_root).endswith("data/corpus_revisado/option_a_public_corpus_v2"))

    def test_build_phase95_corpus_mapping_declares_option_b_as_official_demo_corpus(self) -> None:
        mapping = build_phase95_corpus_mapping().to_dict()
        self.assertEqual(mapping["official_demo_corpus_name"], "option_b_synthetic_premium")
        self.assertTrue(any(item["local_subdir"] == "policies" for item in mapping["nextcloud_directories"]))
        self.assertGreaterEqual(len(mapping["trello_storylines"]), 5)
        self.assertGreaterEqual(len(mapping["notion_registers"]), 3)

    def test_external_targets_status_reports_missing_credentials_by_default(self) -> None:
        with patch.dict(
            os.environ,
            {
                "EVIDENCEOPS_EXTERNAL_SYNC_ENABLED": "false",
                "EVIDENCEOPS_REPOSITORY_BACKEND": "local",
                "EVIDENCEOPS_NEXTCLOUD_BASE_URL": "",
                "EVIDENCEOPS_NEXTCLOUD_USERNAME": "",
                "EVIDENCEOPS_NEXTCLOUD_APP_PASSWORD": "",
                "EVIDENCEOPS_TRELLO_API_KEY": "",
                "EVIDENCEOPS_TRELLO_TOKEN": "",
                "EVIDENCEOPS_TRELLO_BOARD_ID": "",
                "EVIDENCEOPS_TRELLO_LIST_OPEN_ID": "",
                "EVIDENCEOPS_NOTION_API_KEY": "",
                "EVIDENCEOPS_NOTION_DATABASE_ID": "",
            },
            clear=False,
        ):
            status = build_external_targets_status()
            self.assertFalse(status["nextcloud"]["configured"])
            self.assertIn("base_url", status["nextcloud"]["missing"])
            self.assertFalse(status["trello"]["configured"])
            self.assertFalse(status["notion"]["configured"])

    def test_nextcloud_dry_run_builds_upload_plan(self) -> None:
        plan = sync_phase95_corpus_to_nextcloud(dry_run=True)
        self.assertTrue(plan["dry_run"])
        self.assertEqual(plan["official_demo_corpus"], "option_b_synthetic_premium")
        self.assertGreater(plan["planned_upload_count"], 0)

    def test_trello_and_notion_dry_runs_build_storyline_artifacts(self) -> None:
        trello_plan = build_trello_storyline_cards(dry_run=True)
        notion_plan = build_notion_storyline_register_entries(dry_run=True)
        self.assertTrue(trello_plan["dry_run"])
        self.assertGreaterEqual(trello_plan["planned_card_count"], 5)
        self.assertTrue(notion_plan["dry_run"])
        self.assertGreaterEqual(notion_plan["planned_page_count"], 5)

    @patch("src.services.evidenceops_external_targets.WebDavClient.list_tree")
    def test_nextcloud_repository_listing_normalizes_remote_entries(self, mocked_list_tree) -> None:
        mocked_list_tree.return_value = [
            {
                "relative_path": "policies/POL-001_Information_Security_Policy_v1.pdf",
                "display_name": "POL-001_Information_Security_Policy_v1.pdf",
                "size_bytes": 321,
                "modified_at": "Sun, 05 Apr 2026 13:00:00 GMT",
                "etag": '"abc123"',
                "is_collection": False,
            }
        ]

        documents = list_nextcloud_repository_documents(limit=10)

        self.assertEqual(len(documents), 1)
        self.assertEqual(documents[0]["document_id"], "POL-001")
        self.assertEqual(documents[0]["category"], "policies")
        self.assertEqual(documents[0]["repository_backend"], "nextcloud_webdav")
        self.assertEqual(documents[0]["source"], "remote")

    @patch("src.services.evidenceops_local_ops.list_nextcloud_repository_documents")
    def test_local_ops_can_switch_repository_backend_to_nextcloud(self, mocked_remote_list) -> None:
        mocked_remote_list.return_value = [{"relative_path": "policies/POL-001_Information_Security_Policy_v1.pdf"}]

        entries = list_evidenceops_repository_entries(
            repository_root=get_evidenceops_external_settings().corpus_primary_root,
            repository_backend="nextcloud_webdav",
        )

        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["relative_path"], "policies/POL-001_Information_Security_Policy_v1.pdf")


if __name__ == "__main__":
    unittest.main()