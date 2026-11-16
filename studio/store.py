"""SQLite persistence, authenticated teacher accounts, and an append-only action record."""
import hashlib
import json
import os
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = Path(os.environ.get("STUDIO_DATA_DIR", ROOT / "data"))
DB_PATH = DATA / "studio.sqlite3"


def now():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def encode(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value):
    return hashlib.sha256(encode(value).encode()).hexdigest()


@contextmanager
def db(write=False):
    DATA.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH, timeout=20)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys=ON")
    try:
        if write:
            connection.execute("BEGIN IMMEDIATE")
        yield connection
        connection.commit()
    except BaseException:
        connection.rollback()
        raise
    finally:
        connection.close()


def audit(connection, actor, action, inputs, outputs, run_id=None, status="ok"):
    connection.execute(
        "INSERT INTO audit(at,actor,action,inputs,outputs,run_id,status) VALUES(?,?,?,?,?,?,?)",
        (now(), actor, action, encode(inputs), encode(outputs), run_id, status),
    )


def password_hash(password, salt):
    return hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 200000).hex()


def initialise(seed=True):
    DATA.mkdir(parents=True, exist_ok=True)
    with db() as connection:
        connection.execute("PRAGMA journal_mode=WAL")
        connection.executescript("""
        CREATE TABLE IF NOT EXISTS teachers(
          id TEXT PRIMARY KEY, name TEXT NOT NULL, salt TEXT NOT NULL, password_hash TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS sessions(
          token_hash TEXT PRIMARY KEY, teacher_id TEXT NOT NULL REFERENCES teachers(id),
          csrf TEXT NOT NULL, expires REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS learners(
          id TEXT PRIMARY KEY, display_name TEXT NOT NULL, school TEXT NOT NULL,
          grade TEXT NOT NULL, teacher_id TEXT NOT NULL REFERENCES teachers(id),
          consent INTEGER NOT NULL, revision INTEGER NOT NULL DEFAULT 1);
        CREATE TABLE IF NOT EXISTS evidence(
          id TEXT PRIMARY KEY, learner_id TEXT NOT NULL REFERENCES learners(id),
          kind TEXT NOT NULL, skill TEXT NOT NULL, academic_year INTEGER NOT NULL,
          term INTEGER NOT NULL, observed_at TEXT NOT NULL, recorded_at TEXT NOT NULL,
          title TEXT NOT NULL, score REAL, maximum REAL, note TEXT NOT NULL,
          source TEXT NOT NULL, reliable INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS runs(
          id TEXT PRIMARY KEY, learner_id TEXT NOT NULL REFERENCES learners(id),
          teacher_id TEXT NOT NULL REFERENCES teachers(id), status TEXT NOT NULL,
          provider TEXT NOT NULL, model TEXT NOT NULL, started_at TEXT NOT NULL,
          finished_at TEXT, error TEXT, profile_id TEXT, input_tokens INTEGER NOT NULL DEFAULT 0,
          output_tokens INTEGER NOT NULL DEFAULT 0, model_calls INTEGER NOT NULL DEFAULT 0);
        CREATE UNIQUE INDEX IF NOT EXISTS one_active_run ON runs(learner_id)
          WHERE status IN ('queued','running');
        CREATE TABLE IF NOT EXISTS profiles(
          id TEXT PRIMARY KEY, learner_id TEXT NOT NULL REFERENCES learners(id),
          run_id TEXT UNIQUE NOT NULL REFERENCES runs(id), evidence_revision INTEGER NOT NULL,
          content TEXT NOT NULL, content_hash TEXT NOT NULL, state TEXT NOT NULL,
          created_at TEXT NOT NULL, approved_by TEXT REFERENCES teachers(id),
          approved_at TEXT, review_note TEXT, released_by TEXT REFERENCES teachers(id),
          released_at TEXT);
        CREATE TABLE IF NOT EXISTS audit(
          id INTEGER PRIMARY KEY AUTOINCREMENT, at TEXT NOT NULL, actor TEXT NOT NULL,
          action TEXT NOT NULL, inputs TEXT NOT NULL, outputs TEXT NOT NULL,
          run_id TEXT, status TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS audit_run ON audit(run_id,id);
        """)
    with db(True) as connection:
        if not connection.execute("SELECT 1 FROM teachers").fetchone():
            salt = secrets.token_hex(16)
            password = os.environ.get("STUDIO_PASSWORD", "lesson-demo-2026")
            connection.execute("INSERT INTO teachers VALUES(?,?,?,?)", (
                "demo.teacher", os.environ.get("STUDIO_TEACHER_NAME", "Amina Njeri (demo teacher)"),
                salt, password_hash(password, salt)))
        if seed and not connection.execute("SELECT 1 FROM learners").fetchone():
            fixture = json.loads((ROOT / "data" / "synthetic.json").read_text())
            for learner in fixture["learners"]:
                connection.execute("INSERT INTO learners VALUES(?,?,?,?,?,?,?)", (
                    learner["id"], learner["display_name"], "Demo Primary School (synthetic)",
                    "Grade 6", "demo.teacher", 1, 1))
            for row in fixture["evidence"]:
                connection.execute("INSERT INTO evidence VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
                    row["id"], row["learner_id"], row["kind"], row["skill"], row["academic_year"],
                    row["term"], row["observed_at"], row["recorded_at"], row["title"], row["score"],
                    row["maximum"], row["note"], row["source"], int(row["reliable"])))
            audit(connection, "system", "seed_synthetic_records", {}, {
                "learners": len(fixture["learners"]), "evidence": len(fixture["evidence"])})
    return DB_PATH


def learner_record(connection, learner_id):
    row = connection.execute("SELECT * FROM learners WHERE id=?", (learner_id,)).fetchone()
    if row is None:
        raise ValueError("Unknown learner")
    if not row["consent"]:
        raise ValueError("Consent for processing is required")
    return dict(row)
