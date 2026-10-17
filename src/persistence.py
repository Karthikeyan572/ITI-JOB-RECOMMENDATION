"""SQLite persistence and password/session helpers for the ITI candidate portal."""
from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = Path(os.getenv("ITI_DATABASE_PATH", str(PROJECT_ROOT / "data" / "iti_portal.db")))
PBKDF2_ITERATIONS = 310_000
SESSION_DAYS = 14


def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    with connect() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL UNIQUE COLLATE NOCASE,
            password_hash TEXT NOT NULL,
            full_name TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'candidate' CHECK(role IN ('candidate','employer','admin')),
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS sessions (
            token_hash TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            expires_at TEXT NOT NULL, created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS saved_jobs (
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            job_id TEXT NOT NULL, job_json TEXT NOT NULL, created_at TEXT NOT NULL,
            PRIMARY KEY(user_id, job_id)
        );
        CREATE TABLE IF NOT EXISTS applications (
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            job_id TEXT NOT NULL, job_json TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Applied', applied_at TEXT NOT NULL, updated_at TEXT NOT NULL,
            employer_job_post_id INTEGER REFERENCES job_posts(id) ON DELETE SET NULL,
            employer_note TEXT NOT NULL DEFAULT '',
            PRIMARY KEY(user_id, job_id)
        );
        CREATE TABLE IF NOT EXISTS job_posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employer_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            title TEXT NOT NULL, trade TEXT NOT NULL, company TEXT NOT NULL,
            location TEXT NOT NULL, description TEXT NOT NULL,
            required_skills_json TEXT NOT NULL DEFAULT '[]',
            experience_required REAL NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','approved','rejected','closed')),
            created_at TEXT NOT NULL, updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS admin_audit (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            actor_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
            action TEXT NOT NULL, target_type TEXT NOT NULL, target_id TEXT NOT NULL,
            details TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);
        CREATE INDEX IF NOT EXISTS idx_job_posts_status ON job_posts(status);
        """)
        app_columns = {row["name"] for row in conn.execute("PRAGMA table_info(applications)").fetchall()}
        if "employer_job_post_id" not in app_columns:
            conn.execute("ALTER TABLE applications ADD COLUMN employer_job_post_id INTEGER REFERENCES job_posts(id) ON DELETE SET NULL")
        if "employer_note" not in app_columns:
            conn.execute("ALTER TABLE applications ADD COLUMN employer_note TEXT NOT NULL DEFAULT ''")
        schema = conn.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='users'").fetchone()
        if schema and "CHECK(role IN ('candidate'))" in (schema["sql"] or ""):
            conn.execute("PRAGMA foreign_keys=OFF")
            conn.executescript("""
                BEGIN;
                ALTER TABLE users RENAME TO users_phase5_backup;
                CREATE TABLE users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email TEXT NOT NULL UNIQUE COLLATE NOCASE,
                    password_hash TEXT NOT NULL,
                    full_name TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'candidate' CHECK(role IN ('candidate','employer','admin')),
                    created_at TEXT NOT NULL
                );
                INSERT INTO users(id,email,password_hash,full_name,role,created_at)
                    SELECT id,email,password_hash,full_name,role,created_at FROM users_phase5_backup;
                DROP TABLE users_phase5_backup;
                COMMIT;
            """)
            conn.execute("PRAGMA foreign_keys=ON")


def _now():
    return datetime.now(timezone.utc)


def _password_hash(password: str, salt: bytes | None = None):
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt.hex()}${digest.hex()}"


def _verify_password(password: str, encoded: str):
    try:
        scheme, iterations, salt_hex, expected_hex = encoded.split("$")
        if scheme != "pbkdf2_sha256":
            return False
        actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), int(iterations))
        return hmac.compare_digest(actual.hex(), expected_hex)
    except (ValueError, TypeError):
        return False


def create_user(email: str, password: str, full_name: str, role: str = 'candidate'):
    email = email.strip().lower()
    with connect() as conn:
        try:
            cursor = conn.execute(
                "INSERT INTO users(email,password_hash,full_name,role,created_at) VALUES(?,?,?,?,?)",
                (email, _password_hash(password), full_name.strip(), role, _now().isoformat())
            )
        except sqlite3.IntegrityError:
            return None
        return {"id": cursor.lastrowid, "email": email, "full_name": full_name.strip(), "role": role}


def authenticate_user(email: str, password: str):
    with connect() as conn:
        row = conn.execute("SELECT * FROM users WHERE email = ?", (email.strip().lower(),)).fetchone()
    if not row or not _verify_password(password, row["password_hash"]):
        return None
    return {"id": row["id"], "email": row["email"], "full_name": row["full_name"], "role": row["role"]}


def create_session(user_id: int):
    token = secrets.token_urlsafe(32)
    now = _now()
    with connect() as conn:
        conn.execute("DELETE FROM sessions WHERE expires_at < ?", (now.isoformat(),))
        conn.execute(
            "INSERT INTO sessions(token_hash,user_id,expires_at,created_at) VALUES(?,?,?,?)",
            (hashlib.sha256(token.encode()).hexdigest(), user_id,
             (now + timedelta(days=SESSION_DAYS)).isoformat(), now.isoformat())
        )
    return token


def get_user_for_token(token: str):
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    now = _now().isoformat()
    with connect() as conn:
        row = conn.execute(
            """SELECT u.id,u.email,u.full_name,u.role FROM sessions s
               JOIN users u ON u.id=s.user_id WHERE s.token_hash=? AND s.expires_at>?""",
            (token_hash, now)
        ).fetchone()
    return dict(row) if row else None


def revoke_session(token: str):
    with connect() as conn:
        conn.execute("DELETE FROM sessions WHERE token_hash=?", (hashlib.sha256(token.encode()).hexdigest(),))


def list_saved_jobs(user_id: int):
    import json
    with connect() as conn:
        rows = conn.execute("SELECT job_json FROM saved_jobs WHERE user_id=? ORDER BY created_at DESC", (user_id,)).fetchall()
    return [json.loads(row["job_json"]) for row in rows]


def save_job(user_id: int, job_id: str, job: dict):
    import json
    with connect() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO saved_jobs(user_id,job_id,job_json,created_at) VALUES(?,?,?,?)",
            (user_id, job_id, json.dumps(job), _now().isoformat())
        )


def unsave_job(user_id: int, job_id: str):
    with connect() as conn:
        conn.execute("DELETE FROM saved_jobs WHERE user_id=? AND job_id=?", (user_id, job_id))


def list_applications(user_id: int):
    import json
    with connect() as conn:
        rows = conn.execute(
            "SELECT job_json,status,applied_at,updated_at FROM applications WHERE user_id=? ORDER BY applied_at DESC",
            (user_id,)
        ).fetchall()
    result = []
    for row in rows:
        item = json.loads(row["job_json"])
        item.update({"status": row["status"], "applied_at": row["applied_at"], "updated_at": row["updated_at"]})
        result.append(item)
    return result


def add_application(user_id: int, job_id: str, job: dict):
    import json
    now = _now().isoformat()
    with connect() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO applications(user_id,job_id,job_json,status,applied_at,updated_at) VALUES(?,?,?,?,?,?)",
            (user_id, job_id, json.dumps(job), "Applied", now, now)
        )
        row = conn.execute(
            "SELECT job_json,status,applied_at,updated_at FROM applications WHERE user_id=? AND job_id=?",
            (user_id, job_id)
        ).fetchone()
    item = json.loads(row["job_json"])
    item.update({"status": row["status"], "applied_at": row["applied_at"], "updated_at": row["updated_at"]})
    return item


def update_application_status(user_id: int, job_id: str, status: str):
    allowed = {"Applied", "Interview", "Offer", "Rejected", "Withdrawn"}
    if status not in allowed:
        return None
    now = _now().isoformat()
    with connect() as conn:
        cursor = conn.execute(
            "UPDATE applications SET status=?,updated_at=? WHERE user_id=? AND job_id=?",
            (status, now, user_id, job_id)
        )
        if not cursor.rowcount:
            return None
        row = conn.execute(
            "SELECT job_json,status,applied_at,updated_at FROM applications WHERE user_id=? AND job_id=?",
            (user_id, job_id)
        ).fetchone()
    import json
    item = json.loads(row["job_json"])
    item.update({"status": row["status"], "applied_at": row["applied_at"], "updated_at": row["updated_at"]})
    return item


def create_job_post(employer_id: int, data: dict):
    import json
    now = _now().isoformat()
    with connect() as conn:
        cur = conn.execute(
            """INSERT INTO job_posts(employer_id,title,trade,company,location,description,
               required_skills_json,experience_required,status,created_at,updated_at)
               VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
            (employer_id, data["title"].strip(), data["trade"], data["company"].strip(),
             data["location"].strip(), data["description"].strip(),
             json.dumps(data.get("required_skills", [])), float(data.get("experience_required", 0)),
             "pending", now, now))
        return get_job_post(cur.lastrowid, conn)


def get_job_post(post_id: int, conn=None):
    import json
    own = conn is None
    if own: conn = connect()
    row = conn.execute("SELECT * FROM job_posts WHERE id=?", (post_id,)).fetchone()
    if own: conn.close()
    if not row: return None
    item = dict(row)
    item["required_skills"] = json.loads(item.pop("required_skills_json"))
    return item


def list_job_posts(status: str | None = None, employer_id: int | None = None):
    import json
    query = "SELECT * FROM job_posts WHERE 1=1"
    params = []
    if status:
        query += " AND status=?"; params.append(status)
    if employer_id is not None:
        query += " AND employer_id=?"; params.append(employer_id)
    query += " ORDER BY created_at DESC"
    with connect() as conn: rows = conn.execute(query, params).fetchall()
    result = []
    for row in rows:
        item = dict(row); item["required_skills"] = json.loads(item.pop("required_skills_json")); result.append(item)
    return result


def set_job_post_status(post_id: int, status: str):
    if status not in {"pending", "approved", "rejected", "closed"}: return None
    with connect() as conn:
        cur = conn.execute("UPDATE job_posts SET status=?,updated_at=? WHERE id=?", (status,_now().isoformat(),post_id))
        if not cur.rowcount: return None
    return get_job_post(post_id)


def add_admin_audit(actor_id: int, action: str, target_type: str, target_id: str, details: str = ""):
    with connect() as conn:
        conn.execute("INSERT INTO admin_audit(actor_id,action,target_type,target_id,details,created_at) VALUES(?,?,?,?,?,?)",
                     (actor_id,action,target_type,str(target_id),details,_now().isoformat()))


def list_users():
    with connect() as conn:
        rows = conn.execute("SELECT id,email,full_name,role,created_at FROM users ORDER BY created_at DESC").fetchall()
    return [dict(row) for row in rows]


def set_user_role(user_id: int, role: str):
    if role not in {"candidate", "employer", "admin"}: return None
    with connect() as conn:
        cur = conn.execute("UPDATE users SET role=? WHERE id=?", (role,user_id))
        if not cur.rowcount: return None
        row = conn.execute("SELECT id,email,full_name,role,created_at FROM users WHERE id=?", (user_id,)).fetchone()
    return dict(row)


def list_employer_applications(employer_id: int):
    import json
    with connect() as conn:
        rows = conn.execute(
            """SELECT a.user_id,a.job_id,a.job_json,a.status,a.applied_at,a.updated_at,
                      a.employer_note,a.employer_job_post_id,j.title AS posted_title,j.company AS posted_company,
                      u.full_name AS candidate_name,u.email AS candidate_email
               FROM applications a
               JOIN job_posts j ON j.id=a.employer_job_post_id
               JOIN users u ON u.id=a.user_id
               WHERE j.employer_id=? ORDER BY a.applied_at DESC""", (employer_id,)
        ).fetchall()
    result = []
    for row in rows:
        item = dict(row); item["candidate_job"] = json.loads(item.pop("job_json")); result.append(item)
    return result


def link_application_to_job(user_id: int, job_id: str, post_id: int):
    with connect() as conn:
        post = conn.execute("SELECT id,status FROM job_posts WHERE id=?", (post_id,)).fetchone()
        if not post or post["status"] != "approved": return False
        cur = conn.execute(
            "UPDATE applications SET employer_job_post_id=?,updated_at=? WHERE user_id=? AND job_id=?",
            (post_id,_now().isoformat(),user_id,job_id)
        )
        return cur.rowcount > 0


def update_employer_application(employer_id: int, application_user_id: int, job_id: str, status: str, note: str = ""):
    allowed = {"Applied", "Reviewing", "Interview", "Offer", "Rejected", "Withdrawn"}
    if status not in allowed: return None
    now = _now().isoformat()
    with connect() as conn:
        row = conn.execute(
            """SELECT a.user_id,a.job_id,a.job_json,a.status,a.applied_at,a.updated_at,a.employer_note,
                      a.employer_job_post_id,j.id AS post_id,j.title AS posted_title,j.company AS posted_company,
                      u.full_name AS candidate_name,u.email AS candidate_email
               FROM applications a JOIN job_posts j ON j.id=a.employer_job_post_id
               JOIN users u ON u.id=a.user_id
               WHERE j.employer_id=? AND a.user_id=? AND a.job_id=?""",
            (employer_id,application_user_id,job_id)
        ).fetchone()
        if not row: return None
        conn.execute(
            "UPDATE applications SET status=?,employer_note=?,updated_at=? WHERE user_id=? AND job_id=?",
            (status,note[:2000],now,application_user_id,job_id)
        )
        updated = conn.execute(
            """SELECT a.user_id,a.job_id,a.job_json,a.status,a.applied_at,a.updated_at,a.employer_note,
                      a.employer_job_post_id,j.title AS posted_title,j.company AS posted_company,
                      u.full_name AS candidate_name,u.email AS candidate_email
               FROM applications a JOIN job_posts j ON j.id=a.employer_job_post_id
               JOIN users u ON u.id=a.user_id
               WHERE j.employer_id=? AND a.user_id=? AND a.job_id=?""",
            (employer_id,application_user_id,job_id)
        ).fetchone()
    import json
    item = dict(updated); item["candidate_job"] = json.loads(item.pop("job_json")); return item
