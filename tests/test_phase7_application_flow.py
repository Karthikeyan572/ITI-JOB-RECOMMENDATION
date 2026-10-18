import os
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient
from src import persistence


class TestPhase7ApplicationFlow(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_path = persistence.DB_PATH
        persistence.DB_PATH = Path(self.temp_dir.name) / "phase7.db"
        persistence.init_db()
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
        sys.modules.pop("api", None)
        sys.modules.pop("persistence", None)
        import persistence as api_persistence
        api_persistence.DB_PATH = persistence.DB_PATH
        import api
        self.api = api
        self.client = TestClient(api.app)

    def tearDown(self):
        self.client.close()
        persistence.DB_PATH = self.original_path
        import gc
        gc.collect()
        try:
            self.temp_dir.cleanup()
        except Exception:
            pass

    def _register(self, name, email, role):
        response = self.client.post("/api/auth/register", json={
            "full_name": name, "email": email, "password": "StrongPassword123", "role": role
        })
        self.assertEqual(response.status_code, 201, response.text)
        return {"Authorization": "Bearer " + response.json()["access_token"]}

    def test_candidate_workflows_require_a_signed_in_session(self):
        self.assertEqual(self.client.get("/api/health").status_code, 200)
        for path in ("/api/meta", "/api/samples", "/api/job-sources", "/api/learning-sources", "/api/jobs", "/api/jobs/approved", "/api/courses"):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 401)

        self.assertEqual(self.client.post("/api/upload-resume", files={"file": ("resume.txt", b"ITI Electrician")}).status_code, 401)
        self.assertEqual(self.client.post("/api/match-jobs", json={"profile": {"validation_status": "VALID"}}).status_code, 401)

    def test_candidate_application_appears_in_employer_inbox_and_can_be_reviewed(self):
        employer_headers = self._register("Employer", "employer@example.com", "employer")
        candidate_headers = self._register("Candidate", "candidate@example.com", "candidate")
        job_response = self.client.post("/api/employer/jobs", headers=employer_headers, json={
            "title": "ITI Electrician", "trade": "Electrician", "company": "Test Co",
            "location": "Coimbatore", "description": "Electrical installation and maintenance tasks.",
            "required_skills": ["Wiring"], "experience_required": 0
        })
        self.assertEqual(job_response.status_code, 201, job_response.text)
        job = job_response.json()["job"]
        self.assertEqual(job["status"], "approved")
        candidate_job = {
            "job_id": f"EMP-{job['id']}", "job_title": job["title"], "company": job["company"],
            "location": job["location"], "iti_trade": job["trade"], "job_description": job["description"],
            "required_skills": job["required_skills"], "record_status": "EMPLOYER_SUBMITTED"
        }
        applied = self.client.post("/api/account/applications", headers=candidate_headers, json={
            "job": candidate_job, "employer_job_post_id": job["id"]
        })
        self.assertEqual(applied.status_code, 200, applied.text)
        inbox = self.client.get("/api/employer/applications", headers=employer_headers)
        self.assertEqual(inbox.status_code, 200, inbox.text)
        self.assertEqual(len(inbox.json()["applications"]), 1)
        app_record = inbox.json()["applications"][0]
        reviewed = self.client.patch(
            f"/api/employer/applications/{app_record['user_id']}/{app_record['job_id']}",
            headers=employer_headers, json={"status": "Interview", "note": "Schedule a technical interview."}
        )
        self.assertEqual(reviewed.status_code, 200, reviewed.text)
        self.assertEqual(reviewed.json()["application"]["status"], "Interview")
        self.assertEqual(self.client.get("/api/employer/applications", headers=candidate_headers).status_code, 403)


if __name__ == "__main__":
    unittest.main()
