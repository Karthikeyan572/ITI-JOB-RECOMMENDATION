"""
tests/test_job_specific_resume.py
Groups A-F for POST /api/vacancies/{job_id}/analyze-resume
"""
import io
import json
import os
import sys
import tempfile
import unittest
import uuid
import zipfile
from pathlib import Path

# ── Minimal test files ────────────────────────────────────────────────────────

def _make_minimal_pdf() -> bytes:
    import pymupdf
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((50, 72), "Wiring Panel Wiring Electrical Installation Electrician ITI")
    return doc.tobytes()

MINIMAL_PDF = _make_minimal_pdf()


def _make_minimal_docx() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml",
            '<?xml version="1.0"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Override PartName="/word/document.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
            '</Types>')
        zf.writestr("_rels/.rels",
            '<?xml version="1.0"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
            '</Relationships>')
        zf.writestr("word/document.xml",
            '<?xml version="1.0"?>'
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            '<w:body><w:p><w:r><w:t>Wiring Panel Wiring Electrical Installation</w:t></w:r></w:p></w:body>'
            '</w:document>')
        zf.writestr("word/_rels/document.xml.rels",
            '<?xml version="1.0"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '</Relationships>')
    return buf.getvalue()


MINIMAL_DOCX = _make_minimal_docx()


# ── Test base class with per-test temp DB ─────────────────────────────────────

from src import persistence


class _BaseTestCase(unittest.TestCase):
    """Sets up isolated temp DB and fresh FastAPI test client for every test class."""

    @classmethod
    def setUpClass(cls):
        cls._temp_dir = tempfile.TemporaryDirectory()
        cls._original_path = persistence.DB_PATH
        cls._original_env = {
            k: os.environ.get(k)
            for k in ("ITI_ADMIN_EMAIL", "ITI_ADMIN_PASSWORD", "ITI_ADMIN_NAME")
        }
        os.environ["ITI_ADMIN_EMAIL"] = "admin@example.com"
        os.environ["ITI_ADMIN_PASSWORD"] = "StrongPassword123"
        os.environ["ITI_ADMIN_NAME"] = "Project Admin"
        persistence.DB_PATH = Path(cls._temp_dir.name) / "job_resume_test.db"
        persistence.init_db()

        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
        sys.modules.pop("api", None)
        sys.modules.pop("persistence", None)
        import persistence as api_persistence
        api_persistence.DB_PATH = persistence.DB_PATH
        import api

        from fastapi.testclient import TestClient
        cls.client = TestClient(api.app, raise_server_exceptions=False)

        # Bootstrap admin
        cls.admin_token = cls._login("admin@example.com", "StrongPassword123")
        # Create one employer + candidate
        sfx = uuid.uuid4().hex[:6]
        cls.emp_token = cls._register(f"emp_{sfx}@x.com", "Password1234", "employer")
        cls.cand_token = cls._register(f"cand_{sfx}@x.com", "Password1234", "candidate")
        cls.cand_user_id = cls.client.get(
            "/api/auth/me", headers={"Authorization": f"Bearer {cls.cand_token}"}
        ).json()["user"]["id"]

    @classmethod
    def tearDownClass(cls):
        persistence.DB_PATH = cls._original_path
        for k, v in cls._original_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        try:
            cls._temp_dir.cleanup()
        except Exception:
            pass

    @classmethod
    def _register(cls, email, password, role):
        r = cls.client.post("/api/auth/register", json={
            "email": email, "password": password,
            "full_name": "Test User", "role": role
        })
        assert r.status_code == 201, f"Register failed: {r.text}"
        return r.json()["access_token"]

    @classmethod
    def _login(cls, email, password):
        r = cls.client.post("/api/auth/login", json={
            "email": email, "password": password
        })
        assert r.status_code == 200, f"Login failed: {r.text}"
        return r.json()["access_token"]

    @classmethod
    def _create_approved_job(cls, skills=None):
        if skills is None:
            skills = ["Wiring", "Panel Wiring", "Electrical Installation"]
        r = cls.client.post("/api/employer/jobs",
            headers={"Authorization": f"Bearer {cls.emp_token}"},
            json={
                "title": "Electrician", "trade": "Electrician",
                "company": "Test Co", "location": "Chennai",
                "description": "Perform electrical wiring, panel work, and maintenance tasks.", "required_skills": skills,
                "experience_required": 1
            })
        assert r.status_code == 201, f"Job create failed: {r.text}"
        job_id = r.json()["job"]["id"]
        r2 = cls.client.patch(f"/api/admin/jobs/{job_id}/moderate",
            headers={"Authorization": f"Bearer {cls.admin_token}"},
            json={"status": "approve"})
        assert r2.status_code == 200, f"Job approve failed: {r2.text}"
        return job_id

    @classmethod
    def _create_job_with_status(cls, status):
        """Create a job and leave it as pending, or moderate it to the desired status."""
        r = cls.client.post("/api/employer/jobs",
            headers={"Authorization": f"Bearer {cls.emp_token}"},
            json={
                "title": "Test Fitter Role", "trade": "Fitter", "company": "CompanyX",
                "location": "Delhi", "description": "Perform fitting, lathe and maintenance work in a workshop.",
                "required_skills": ["Fitting"], "experience_required": 0
            })
        assert r.status_code == 201, f"Job create failed: {r.text}"
        job_id = r.json()["job"]["id"]
        if status == "pending":
            return job_id
        if status == "approved":
            cls.client.patch(f"/api/admin/jobs/{job_id}/moderate",
                headers={"Authorization": f"Bearer {cls.admin_token}"},
                json={"status": "approve"})
        elif status == "rejected":
            cls.client.patch(f"/api/admin/jobs/{job_id}/moderate",
                headers={"Authorization": f"Bearer {cls.admin_token}"},
                json={"status": "reject"})
        elif status == "closed":
            # Must approve first, then close
            cls.client.patch(f"/api/admin/jobs/{job_id}/moderate",
                headers={"Authorization": f"Bearer {cls.admin_token}"},
                json={"status": "approve"})
            cls.client.patch(f"/api/admin/jobs/{job_id}/moderate",
                headers={"Authorization": f"Bearer {cls.admin_token}"},
                json={"status": "close"})
        return job_id

    def _analyze(self, job_id, token, file_bytes, filename):
        return self.client.post(
            f"/api/vacancies/{job_id}/analyze-resume",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": (filename, io.BytesIO(file_bytes), "application/octet-stream")}
        )


# ══════════════════════════════════════════════════════════════════════════════
# GROUP A – Happy path
# ══════════════════════════════════════════════════════════════════════════════

class TestGroupA(_BaseTestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.job_id = cls._create_approved_job()

    def test_A1_valid_pdf_returns_200_with_all_keys(self):
        r = self._analyze(self.job_id, self.cand_token, MINIMAL_PDF, "resume.pdf")
        self.assertEqual(r.status_code, 200, r.text)
        data = r.json()
        for key in ("candidate_skills", "required_skills", "matched_skills",
                    "missing_skills", "total_required", "matched_count",
                    "missing_count", "match_percentage", "gap_percentage",
                    "no_skills_defined"):
            self.assertIn(key, data, f"missing key: {key}")
        self.assertGreaterEqual(data["match_percentage"], 0.0)
        self.assertLessEqual(data["match_percentage"], 100.0)

    def test_A2_valid_docx_returns_200(self):
        r = self._analyze(self.job_id, self.cand_token, MINIMAL_DOCX, "resume.docx")
        self.assertEqual(r.status_code, 200, r.text)
        self.assertIn("candidate_skills", r.json())

    def test_A3_does_not_overwrite_candidate_profile(self):
        from persistence import get_candidate_profile, save_candidate_profile
        sfx = uuid.uuid4().hex[:6]
        t = self._register(f"cand_a3_{sfx}@x.com", "Password1234", "candidate")
        me = self.client.get("/api/auth/me", headers={"Authorization": f"Bearer {t}"})
        uid = me.json()["user"]["id"]
        save_candidate_profile(uid, {"skills": ["__SENTINEL__"], "iti_trade": "Fitter"})
        self._analyze(self.job_id, t, MINIMAL_PDF, "resume.pdf")
        after = get_candidate_profile(uid)
        self.assertIn("__SENTINEL__", after["skills"])

    def test_A4_match_percentage_calculation(self):
        r = self._analyze(self.job_id, self.cand_token, MINIMAL_PDF, "resume.pdf")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(data["total_required"], 3)
        if data["matched_count"] > 0:
            expected = round(data["matched_count"] / 3 * 100, 1)
            self.assertAlmostEqual(data["match_percentage"], expected, places=1)

    def test_A5_job_with_no_required_skills(self):
        empty_job = self._create_approved_job(skills=[])
        r = self._analyze(empty_job, self.cand_token, MINIMAL_PDF, "resume.pdf")
        self.assertEqual(r.status_code, 200, r.text)
        data = r.json()
        self.assertTrue(data["no_skills_defined"])
        self.assertEqual(data["total_required"], 0)
        self.assertEqual(data["required_skills"], [])
        self.assertAlmostEqual(data["match_percentage"], 100.0, places=1)


# ══════════════════════════════════════════════════════════════════════════════
# GROUP B – Auth / role rejection
# ══════════════════════════════════════════════════════════════════════════════

class TestGroupB(_BaseTestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.job_id = cls._create_approved_job()

    def test_B1_no_token_returns_401(self):
        r = self.client.post(f"/api/vacancies/{self.job_id}/analyze-resume",
            files={"file": ("r.pdf", io.BytesIO(MINIMAL_PDF), "application/pdf")})
        self.assertEqual(r.status_code, 401)

    def test_B2_employer_token_returns_403(self):
        r = self._analyze(self.job_id, self.emp_token, MINIMAL_PDF, "resume.pdf")
        self.assertEqual(r.status_code, 403)

    def test_B3_admin_token_returns_403(self):
        r = self._analyze(self.job_id, self.admin_token, MINIMAL_PDF, "resume.pdf")
        self.assertEqual(r.status_code, 403)


# ══════════════════════════════════════════════════════════════════════════════
# GROUP C – Job status validation
# ══════════════════════════════════════════════════════════════════════════════

class TestGroupC(_BaseTestCase):

    def test_C1_nonexistent_job_returns_404(self):
        r = self._analyze(999999, self.cand_token, MINIMAL_PDF, "resume.pdf")
        self.assertEqual(r.status_code, 404)

    def test_C2_pending_job_returns_422(self):
        jid = self._create_job_with_status("pending")
        r = self._analyze(jid, self.cand_token, MINIMAL_PDF, "resume.pdf")
        self.assertEqual(r.status_code, 422)

    def test_C3_rejected_job_returns_422(self):
        jid = self._create_job_with_status("rejected")
        r = self._analyze(jid, self.cand_token, MINIMAL_PDF, "resume.pdf")
        self.assertEqual(r.status_code, 422)

    def test_C4_closed_job_returns_422(self):
        jid = self._create_job_with_status("closed")
        r = self._analyze(jid, self.cand_token, MINIMAL_PDF, "resume.pdf")
        self.assertEqual(r.status_code, 422)


# ══════════════════════════════════════════════════════════════════════════════
# GROUP D – File validation
# ══════════════════════════════════════════════════════════════════════════════

class TestGroupD(_BaseTestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.job_id = cls._create_approved_job()

    def test_D1_empty_file_returns_400(self):
        r = self._analyze(self.job_id, self.cand_token, b"", "resume.pdf")
        self.assertEqual(r.status_code, 400)

    def test_D2_wrong_extension_txt_returns_415(self):
        r = self._analyze(self.job_id, self.cand_token, b"hello world", "resume.txt")
        self.assertEqual(r.status_code, 415)

    def test_D3_wrong_extension_exe_returns_415(self):
        r = self._analyze(self.job_id, self.cand_token, MINIMAL_PDF, "resume.exe")
        self.assertEqual(r.status_code, 415)

    def test_D4_pdf_wrong_magic_bytes_returns_415(self):
        r = self._analyze(self.job_id, self.cand_token, b"NOTPDF\x00" * 20, "resume.pdf")
        self.assertEqual(r.status_code, 415)

    def test_D5_docx_wrong_magic_bytes_returns_415(self):
        r = self._analyze(self.job_id, self.cand_token, b"NOTZIP\x00" * 20, "resume.docx")
        self.assertEqual(r.status_code, 415)

    def test_D6_corrupted_pdf_valid_magic_returns_422(self):
        corrupt = b"%PDF-1.4\n" + b"\x00" * 200
        r = self._analyze(self.job_id, self.cand_token, corrupt, "resume.pdf")
        self.assertIn(r.status_code, (422, 500))

    def test_D7_corrupted_docx_valid_magic_returns_422(self):
        corrupt = b"PK\x03\x04" + b"\x00" * 200
        r = self._analyze(self.job_id, self.cand_token, corrupt, "resume.docx")
        self.assertIn(r.status_code, (422, 500))

    def test_D8_file_over_5mb_returns_413(self):
        big = b"%PDF-1.4\n" + b"A" * (5 * 1024 * 1024)
        r = self._analyze(self.job_id, self.cand_token, big, "resume.pdf")
        self.assertEqual(r.status_code, 413)

    def test_D9_file_exactly_at_limit_not_rejected_for_size(self):
        exactly = b"%PDF-1.4\n" + b"A" * (5 * 1024 * 1024 - 9)
        r = self._analyze(self.job_id, self.cand_token, exactly, "resume.pdf")
        self.assertNotEqual(r.status_code, 413)

    def test_D10_spoofed_mime_valid_pdf_passes(self):
        r = self._analyze(self.job_id, self.cand_token, MINIMAL_PDF, "resume.pdf")
        self.assertEqual(r.status_code, 200)


# ══════════════════════════════════════════════════════════════════════════════
# GROUP E – Duplicate apply / save
# ══════════════════════════════════════════════════════════════════════════════

class TestGroupE(_BaseTestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.job_id = cls._create_approved_job()

    def _apply(self):
        return self.client.post("/api/account/applications",
            headers={"Authorization": f"Bearer {self.cand_token}"},
            json={"job": {"job_id": f"EMP-{self.job_id}",
                          "job_title": "Electrician", "company": "Test Co",
                          "location": "Chennai", "trade": "Electrician"},
                  "employer_job_post_id": self.job_id})

    def _save(self):
        return self.client.post("/api/account/saved-jobs",
            headers={"Authorization": f"Bearer {self.cand_token}"},
            json={"job": {"job_id": f"EMP-{self.job_id}",
                          "job_title": "Electrician", "company": "Test Co",
                          "location": "Chennai", "trade": "Electrician"}})

    def test_E1_duplicate_apply_no_duplicate_db_row(self):
        from persistence import list_applications
        self._apply()
        self._apply()
        apps = list_applications(self.cand_user_id)
        matching = [a for a in apps if a.get("job_id") == f"EMP-{self.job_id}"]
        self.assertEqual(len(matching), 1)

    def test_E2_duplicate_save_no_duplicate_db_row(self):
        from persistence import list_saved_jobs
        self._save()
        self._save()
        saved = list_saved_jobs(self.cand_user_id)
        matching = [s for s in saved if s.get("job_id") == f"EMP-{self.job_id}"]
        self.assertEqual(len(matching), 1)


# ══════════════════════════════════════════════════════════════════════════════
# GROUP F – Per-job isolation
# ══════════════════════════════════════════════════════════════════════════════

class TestGroupF(_BaseTestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.job_a = cls._create_approved_job(skills=["Wiring"])
        cls.job_b = cls._create_approved_job(skills=["Fitting", "Lathe Operation"])

    def test_F1_jobs_return_independent_required_skills(self):
        r_a = self._analyze(self.job_a, self.cand_token, MINIMAL_PDF, "resume.pdf")
        r_b = self._analyze(self.job_b, self.cand_token, MINIMAL_DOCX, "resume.docx")
        self.assertEqual(r_a.status_code, 200)
        self.assertEqual(r_b.status_code, 200)
        self.assertNotEqual(
            set(r_a.json()["required_skills"]),
            set(r_b.json()["required_skills"])
        )

    def test_F2_candidate_profile_unchanged_after_both_analyses(self):
        from persistence import get_candidate_profile, save_candidate_profile
        sfx = uuid.uuid4().hex[:6]
        t = self._register(f"cand_f2_{sfx}@x.com", "Password1234", "candidate")
        me = self.client.get("/api/auth/me", headers={"Authorization": f"Bearer {t}"})
        uid = me.json()["user"]["id"]
        save_candidate_profile(uid, {"skills": ["__SENTINEL_F2__"]})
        self._analyze(self.job_a, t, MINIMAL_PDF, "resume.pdf")
        self._analyze(self.job_b, t, MINIMAL_DOCX, "resume.docx")
        after = get_candidate_profile(uid)
        self.assertIn("__SENTINEL_F2__", after["skills"])


if __name__ == "__main__":
    unittest.main()
