import os
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient
from src import persistence


class TestTwoPortals(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_path = persistence.DB_PATH
        self.original_admin_env = {
            key: os.environ.get(key)
            for key in ("ITI_ADMIN_EMAIL", "ITI_ADMIN_PASSWORD", "ITI_ADMIN_NAME")
        }
        os.environ["ITI_ADMIN_EMAIL"] = "admin@example.com"
        os.environ["ITI_ADMIN_PASSWORD"] = "StrongPassword123"
        os.environ["ITI_ADMIN_NAME"] = "Project Admin"
        persistence.DB_PATH = Path(self.temp_dir.name) / "two_portals.db"
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
        for key, value in self.original_admin_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
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

    def _admin_headers(self):
        login = self.client.post("/api/auth/login", json={
            "email": "admin@example.com", "password": "StrongPassword123"
        })
        self.assertEqual(login.status_code, 200, login.text)
        return {"Authorization": "Bearer " + login.json()["access_token"]}

    def test_admin_job_moderation_transitions(self):
        employer_headers = self._register("Employer", "employer@example.com", "employer")
        admin_headers = self._admin_headers()

        # Submit a job
        res = self.client.post("/api/employer/jobs", headers=employer_headers, json={
            "title": "Electrician", "trade": "Electrician", "company": "moto inc.",
            "location": "Bengaluru", "description": "Industrial wiring and electrical maintenance.",
            "required_skills": ["Electrical Wiring", "Troubleshooting", "Motor Testing"],
            "experience_required": 1
        })
        self.assertEqual(res.status_code, 201)
        job_id = res.json()["job"]["id"]
        self.assertEqual(res.json()["job"]["status"], "pending")

        # Non-admin cannot moderate
        candidate_headers = self._register("Candidate", "candidate@example.com", "candidate")
        self.assertEqual(
            self.client.patch(f"/api/admin/jobs/{job_id}/moderate", headers=candidate_headers, json={"status": "approve"}).status_code,
            403
        )

        # Transition Pending -> Approved
        mod_res = self.client.patch(f"/api/admin/jobs/{job_id}/moderate", headers=admin_headers, json={"status": "approve"})
        self.assertEqual(mod_res.status_code, 200)
        self.assertEqual(mod_res.json()["job"]["status"], "approved")

        # Invalid transition: Approved -> Pending (disallowed)
        inv_res = self.client.patch(f"/api/admin/jobs/{job_id}/moderate", headers=admin_headers, json={"status": "approve"})
        self.assertEqual(inv_res.status_code, 422)

        # Transition Approved -> Closed
        close_res = self.client.patch(f"/api/admin/jobs/{job_id}/moderate", headers=admin_headers, json={"status": "close"})
        self.assertEqual(close_res.status_code, 200)
        self.assertEqual(close_res.json()["job"]["status"], "closed")

        # Invalid transition: Closed -> Approved (disallowed)
        reopen_res = self.client.patch(f"/api/admin/jobs/{job_id}/moderate", headers=admin_headers, json={"status": "approve"})
        self.assertEqual(reopen_res.status_code, 422)

    def test_candidate_vacancies_and_skill_gap_analysis(self):
        employer_headers = self._register("Employer", "employer2@example.com", "employer")
        admin_headers = self._admin_headers()
        cand_headers = self._register("John ITI", "john@example.com", "candidate")

        # Create two jobs: one to approve, one rejected
        res1 = self.client.post("/api/employer/jobs", headers=employer_headers, json={
            "title": "Electrician", "trade": "Electrician", "company": "moto inc.",
            "location": "Bengaluru", "description": "Maintain industrial equipment and wiring systems.",
            "required_skills": ["Wiring", "Panel Wiring", "Electrical Installation", "Troubleshooting", "Motor Maintenance"],
            "experience_required": 1
        })
        job1_id = res1.json()["job"]["id"]

        res2 = self.client.post("/api/employer/jobs", headers=employer_headers, json={
            "title": "Fitter", "trade": "Fitter", "company": "steel works",
            "location": "Pune", "description": "Assemble piping components.",
            "required_skills": ["Bench Work"], "experience_required": 0
        })
        job2_id = res2.json()["job"]["id"]

        # Approve job 1, reject job 2
        self.client.patch(f"/api/admin/jobs/{job1_id}/moderate", headers=admin_headers, json={"status": "approve"})
        self.client.patch(f"/api/admin/jobs/{job2_id}/moderate", headers=admin_headers, json={"status": "reject"})

        # Only approved job 1 must appear in candidate vacancies
        vac_res = self.client.get("/api/jobs/approved", headers=cand_headers)
        self.assertEqual(vac_res.status_code, 200)
        job_ids = [j["id"] for j in vac_res.json()["jobs"]]
        self.assertIn(job1_id, job_ids)
        self.assertNotIn(job2_id, job_ids)

        # Candidate skill gap without profile returns has_profile: False
        gap_before = self.client.post(f"/api/vacancies/{job1_id}/skill-gap", headers=cand_headers)
        self.assertEqual(gap_before.status_code, 200)
        self.assertFalse(gap_before.json()["has_profile"])
        self.assertIn("A resume with extracted skills is required", gap_before.json()["message"])

        # Upload candidate resume
        resume_content = (
            b"John ITI\n"
            b"Summary: ITI Electrician candidate\n"
            b"Skills: Wiring, Panel Wiring, Electrical Installation\n"
            b"Education: ITI Electrician\n"
            b"Experience: 2 years in electrical maintenance\n"
        )
        up_res = self.client.post("/api/upload-resume", headers=cand_headers, files={"file": ("john_resume.txt", resume_content)})
        self.assertEqual(up_res.status_code, 200)

        # Now run skill gap analysis
        gap_after = self.client.post(f"/api/vacancies/{job1_id}/skill-gap", headers=cand_headers)
        self.assertEqual(gap_after.status_code, 200)
        gap_data = gap_after.json()
        self.assertTrue(gap_data["has_profile"])
        self.assertEqual(len(gap_data["matched_skills"]), 3)
        self.assertEqual(len(gap_data["missing_skills"]), 2)
        self.assertEqual(gap_data["match_percentage"], 60.0)

        # Candidate Apply creates application record without changing job status
        apply_job_payload = {
            "job_id": f"EMP-{job1_id}",
            "job_title": "Electrician",
            "company": "moto inc.",
            "location": "Bengaluru",
            "iti_trade": "Electrician",
            "job_description": "Maintain industrial equipment and wiring systems.",
            "required_skills": ["Electrical Wiring", "Circuit Installation"],
            "record_status": "EMPLOYER_SUBMITTED_ADMIN_APPROVED"
        }
        apply_res = self.client.post("/api/account/applications", headers=cand_headers, json={
            "job": apply_job_payload,
            "employer_job_post_id": job1_id
        })
        self.assertEqual(apply_res.status_code, 200)

        # Job 1 must STILL be approved
        recheck_vac = self.client.get("/api/jobs/approved", headers=cand_headers)
        self.assertIn(job1_id, [j["id"] for j in recheck_vac.json()["jobs"]])

        # Candidate Save creates saved job record
        save_res = self.client.post("/api/account/saved-jobs", headers=cand_headers, json={
            "job": apply_job_payload
        })
        self.assertEqual(save_res.status_code, 200)
        self.assertTrue(save_res.json()["saved"])


if __name__ == "__main__":
    unittest.main()
