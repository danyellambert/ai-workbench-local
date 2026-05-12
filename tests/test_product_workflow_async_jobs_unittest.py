from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from src.product.access_control import RequestIdentity
from src.product.api import (
    _WORKFLOW_JOBS,
    _cleanup_workflow_jobs,
    _workflow_job_owner_matches,
    _workflow_job_owner_payload,
    _workflow_job_public_payload,
)


class ProductWorkflowAsyncJobsTest(unittest.TestCase):
    def tearDown(self):
        _WORKFLOW_JOBS.clear()

    def _public_identity(self, session_id: str, root: Path) -> RequestIdentity:
        return RequestIdentity(
            role="public",
            user_id=session_id,
            session_id=session_id,
            overlay_root=root / "public_sessions" / session_id / "overlay",
            can_write_global=False,
            can_publish_external=False,
        )

    def _admin_identity(self, root: Path) -> RequestIdentity:
        return RequestIdentity(
            role="admin",
            user_id="admin",
            session_id=None,
            overlay_root=root / "admin" / "overlay",
            can_write_global=True,
            can_publish_external=True,
        )

    def test_public_job_owner_matches_only_same_session(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            user_a = self._public_identity("sess_a123456789012345678901234", root)
            user_b = self._public_identity("sess_b123456789012345678901234", root)
            admin = self._admin_identity(root)

            owner = _workflow_job_owner_payload(user_a)

            self.assertTrue(_workflow_job_owner_matches(user_a, owner))
            self.assertFalse(_workflow_job_owner_matches(user_b, owner))
            self.assertFalse(_workflow_job_owner_matches(admin, owner))

    def test_public_job_owner_rejects_missing_or_blank_session(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            user = self._public_identity("sess_a123456789012345678901234", root)

            self.assertFalse(_workflow_job_owner_matches(user, None))
            self.assertFalse(_workflow_job_owner_matches(user, {}))
            self.assertFalse(_workflow_job_owner_matches(user, {"role": "public", "user_id": user.user_id, "session_id": ""}))

    def test_admin_job_owner_matches_only_admin_identity(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            admin = self._admin_identity(root)
            public_user = self._public_identity("sess_a123456789012345678901234", root)

            owner = _workflow_job_owner_payload(admin)

            self.assertTrue(_workflow_job_owner_matches(admin, owner))
            self.assertFalse(_workflow_job_owner_matches(public_user, owner))

    def test_public_payload_does_not_expose_owner_or_execution_gate(self):
        payload = _workflow_job_public_payload(
            {
                "ok": True,
                "job_id": "workflow_job_test",
                "status": "running",
                "workflow_id": "document_review",
                "write_scope": "session_overlay",
                "owner": {"session_id": "sess_secret"},
                "execution_gate": {"token": "secret"},
                "created_at": "2026-05-11T00:00:00+00:00",
                "updated_at": "2026-05-11T00:00:01+00:00",
            }
        )

        self.assertEqual(payload["job_id"], "workflow_job_test")
        self.assertEqual(payload["status"], "running")
        self.assertNotIn("owner", payload)
        self.assertNotIn("execution_gate", payload)

    def test_cleanup_removes_only_stale_completed_or_error_jobs(self):
        _WORKFLOW_JOBS.update(
            {
                "fresh_completed": {"status": "completed", "created_ts": 2000.0},
                "stale_completed": {"status": "completed", "created_ts": 1.0},
                "stale_error": {"status": "error", "created_ts": 1.0},
                "stale_running": {"status": "running", "created_ts": 1.0},
            }
        )

        _cleanup_workflow_jobs(now=5000.0)

        self.assertIn("fresh_completed", _WORKFLOW_JOBS)
        self.assertNotIn("stale_completed", _WORKFLOW_JOBS)
        self.assertNotIn("stale_error", _WORKFLOW_JOBS)
        self.assertIn("stale_running", _WORKFLOW_JOBS)


if __name__ == "__main__":
    unittest.main()
