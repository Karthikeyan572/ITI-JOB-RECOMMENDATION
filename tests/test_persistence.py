import os
import tempfile
import unittest
from pathlib import Path

from src import persistence


class TestPersistence(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_path = persistence.DB_PATH
        persistence.DB_PATH = Path(self.temp_dir.name) / "test.db"
        persistence.init_db()

    def tearDown(self):
        persistence.DB_PATH = self.original_path
        import gc
        gc.collect()
        try:
            self.temp_dir.cleanup()
        except Exception:
            pass

    def test_register_authenticate_and_session_revoke(self):
        user = persistence.create_user("candidate@example.com", "StrongPassword123", "Test Candidate")
        self.assertIsNotNone(user)
        self.assertIsNone(persistence.create_user("candidate@example.com", "OtherPassword123", "Duplicate"))
        self.assertIsNotNone(persistence.authenticate_user("CANDIDATE@example.com", "StrongPassword123"))
        self.assertIsNone(persistence.authenticate_user("candidate@example.com", "wrong-password"))
        token = persistence.create_session(user["id"])
        self.assertEqual(persistence.get_user_for_token(token)["email"], "candidate@example.com")
        persistence.revoke_session(token)
        self.assertIsNone(persistence.get_user_for_token(token))

    def test_saved_jobs_and_applications_are_user_scoped(self):
        user_a = persistence.create_user("a@example.com", "StrongPassword123", "Candidate A")
        user_b = persistence.create_user("b@example.com", "StrongPassword123", "Candidate B")
        job = {"job_id": "J-1", "job_title": "Electrician"}
        persistence.save_job(user_a["id"], "J-1", job)
        self.assertEqual(len(persistence.list_saved_jobs(user_a["id"])), 1)
        self.assertEqual(persistence.list_saved_jobs(user_b["id"]), [])
        persistence.add_application(user_a["id"], "J-1", job)
        persistence.add_application(user_a["id"], "J-1", job)
        self.assertEqual(len(persistence.list_applications(user_a["id"])), 1)
        updated = persistence.update_application_status(user_a["id"], "J-1", "Interview")
        self.assertEqual(updated["status"], "Interview")
        self.assertIsNone(persistence.update_application_status(user_a["id"], "J-1", "made-up-status"))


if __name__ == "__main__":
    unittest.main()
