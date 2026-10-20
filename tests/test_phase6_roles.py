import os
import tempfile
import unittest
from pathlib import Path

from src import persistence


class TestPhase6Roles(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_path = persistence.DB_PATH
        persistence.DB_PATH = Path(self.temp_dir.name) / "roles.db"
        persistence.init_db()

    def tearDown(self):
        persistence.DB_PATH = self.original_path
        import gc
        gc.collect()
        try:
            self.temp_dir.cleanup()
        except Exception:
            pass

    def test_employer_job_submission_waits_for_review(self):
        employer = persistence.create_user("employer@example.com", "StrongPassword123", "Employer", "employer")
        job = persistence.create_job_post(employer["id"], {
            "title": "Electrician", "trade": "Electrician", "company": "Example Co",
            "location": "Chennai", "description": "Electrical maintenance and installation work.",
            "required_skills": ["Wiring"], "experience_required": 0
        })
        self.assertEqual(job["status"], "pending")
        self.assertEqual(persistence.list_job_posts(status="approved"), [])
        self.assertEqual(len(persistence.list_job_posts(status="pending")), 1)

    def test_job_moderation_and_role_management(self):
        admin = persistence.create_user("admin@example.com", "StrongPassword123", "Admin", "admin")
        employer = persistence.create_user("employer@example.com", "StrongPassword123", "Employer", "employer")
        job = persistence.create_job_post(employer["id"], {
            "title": "Fitter", "trade": "Fitter", "company": "Example Co",
            "location": "Erode", "description": "Fit and assemble industrial mechanical components.",
            "required_skills": [], "experience_required": 1
        })
        approved = persistence.set_job_post_status(job["id"], "approved")
        self.assertEqual(approved["status"], "approved")
        self.assertEqual(len(persistence.list_job_posts(status="approved")), 1)
        self.assertEqual(persistence.set_job_post_status(job["id"], "nonsense"), None)
        changed = persistence.set_user_role(employer["id"], "candidate")
        self.assertEqual(changed["role"], "candidate")
        self.assertEqual(persistence.set_user_role(admin["id"], "root"), None)
        self.assertEqual(persistence.set_user_role(employer["id"], "admin"), None)

    def test_configured_admin_is_seeded_and_password_rotation_revokes_sessions(self):
        admin = persistence.ensure_configured_admin("admin@example.com", "OriginalPassword123", "Project Admin")
        token = persistence.create_session(admin["id"])
        self.assertIsNotNone(persistence.get_user_for_token(token))
        self.assertEqual(persistence.authenticate_user("admin@example.com", "OriginalPassword123")["role"], "admin")

        rotated = persistence.ensure_configured_admin("admin@example.com", "RotatedPassword123", "Project Admin")
        self.assertEqual(rotated["id"], admin["id"])
        self.assertIsNone(persistence.get_user_for_token(token))
        self.assertIsNone(persistence.authenticate_user("admin@example.com", "OriginalPassword123"))
        self.assertEqual(persistence.authenticate_user("admin@example.com", "RotatedPassword123")["role"], "admin")

    def test_configured_admin_does_not_take_over_an_existing_user(self):
        user = persistence.create_user("same@example.com", "StrongPassword123", "Existing User", "candidate")
        with self.assertRaises(ValueError):
            persistence.ensure_configured_admin("same@example.com", "NewPassword123", "Admin")
        self.assertEqual(persistence.authenticate_user("same@example.com", "StrongPassword123")["id"], user["id"])


if __name__ == "__main__":
    unittest.main()
