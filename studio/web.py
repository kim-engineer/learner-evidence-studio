"""Authenticated teacher workspace and controlled profile review."""
import asyncio
import hashlib
import json
import os
import secrets
import sqlite3
import time
import uuid
from contextlib import asynccontextmanager
from urllib.parse import urlparse

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from datetime import date

from . import evidence
from .agent import create_run, execute_run
from .model import MODEL_ID
from .moodle import fetch_mapped_grades
from .store import ROOT, audit, db, digest, initialise, now, password_hash

tasks = set()
run_lock = asyncio.Semaphore(1)
login_attempts = {}


@asynccontextmanager
async def lifespan(app):
    initialise()
    with db(True) as connection:
        abandoned = connection.execute("SELECT id FROM runs WHERE status IN ('queued','running')").fetchall()
        for row in abandoned:
            connection.execute("UPDATE runs SET status='failed',finished_at=?,error=? WHERE id=?",
                               (now(), "Server restarted. Review the saved trace and start a fresh run.", row["id"]))
            audit(connection, "system", "restart_recovery", {}, {"run_id": row["id"]}, row["id"], "error")
    yield
    for task in list(tasks):
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)


app = FastAPI(title="Learner Evidence Studio", lifespan=lifespan)


@app.middleware("http")
async def response_security(request, call_next):
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        origin = request.headers.get("origin")
        if origin and urlparse(origin).netloc != request.headers.get("host"):
            return JSONResponse({"detail": "Cross-origin requests are blocked"}, status_code=403)
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; frame-ancestors 'none'"
    return response


@app.exception_handler(ValueError)
async def value_error(request, exc):
    return JSONResponse({"detail": str(exc)}, status_code=400)


def teacher(request: Request):
    token = request.cookies.get("studio_session", "")
    with db() as connection:
        row = connection.execute("""SELECT t.id,t.name,s.csrf,s.expires FROM sessions s
            JOIN teachers t ON t.id=s.teacher_id WHERE s.token_hash=?""",
            (hashlib.sha256(token.encode()).hexdigest(),)).fetchone()
    if row is None or row["expires"] < time.time():
        raise HTTPException(401, "Sign in to the teacher workspace")
    if request.method not in {"GET", "HEAD"} and not secrets.compare_digest(request.headers.get("x-csrf-token", ""), row["csrf"]):
        raise HTTPException(403, "The request is missing its session verification token")
    return dict(row)


def assigned(connection, learner_id, actor):
    learner = evidence.learner_record(connection, learner_id)
    if learner["teacher_id"] != actor["id"]:
        raise HTTPException(403, "This learner is outside your assignment")
    return learner


class Login(BaseModel):
    username: str = Field(max_length=100)
    password: str = Field(max_length=200)


@app.post("/api/login")
def login(body: Login, request: Request, response: Response):
    remote = request.client.host if request.client else "local"
    attempts = [t for t in login_attempts.get(remote, []) if t > time.time()-60]
    login_attempts[remote] = attempts
    if len(attempts) >= 10:
        raise HTTPException(429, "Wait a minute before another sign-in attempt")
    attempts.append(time.time())
    with db(True) as connection:
        row = connection.execute("SELECT * FROM teachers WHERE id=?", (body.username,)).fetchone()
        if row is None or not secrets.compare_digest(password_hash(body.password, row["salt"]), row["password_hash"]):
            raise HTTPException(401, "Check your username and password")
        token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(24)
        connection.execute("DELETE FROM sessions WHERE expires<?", (time.time(),))
        connection.execute("INSERT INTO sessions VALUES(?,?,?,?)",
                           (hashlib.sha256(token.encode()).hexdigest(), row["id"], csrf, time.time()+8*3600))
        audit(connection, row["id"], "teacher_sign_in", {}, {"authenticated": True})
    response.set_cookie("studio_session", token, httponly=True, samesite="strict",
                        secure=request.url.scheme == "https", max_age=8*3600)
    return {"id": row["id"], "name": row["name"], "csrf": csrf}


@app.get("/api/me")
def me(actor=Depends(teacher)):
    return {**actor, "model": MODEL_ID, "gemini_configured": bool(os.environ.get("GEMINI_API_KEY")),
            "moodle_configured": bool(os.environ.get("MOODLE_URL") and os.environ.get("MOODLE_TOKEN"))}


@app.post("/api/logout")
def logout(request: Request, response: Response, actor=Depends(teacher)):
    with db(True) as connection:
        connection.execute("DELETE FROM sessions WHERE token_hash=?",
                           (hashlib.sha256(request.cookies.get("studio_session", "").encode()).hexdigest(),))
    response.delete_cookie("studio_session")
    return {"signed_out": True}


@app.get("/api/learners")
def learners(actor=Depends(teacher)):
    with db() as connection:
        return [dict(row) for row in connection.execute(
            "SELECT * FROM learners WHERE teacher_id=? ORDER BY id", (actor["id"],))]


class NewLearner(BaseModel):
    display_name: str = Field(min_length=1, max_length=60)
    school: str = Field(min_length=1, max_length=100)
    grade: str = Field(min_length=1, max_length=30)
    consent_confirmed: bool


@app.post("/api/learners")
def new_learner(body: NewLearner, actor=Depends(teacher)):
    if not body.consent_confirmed or not all(s.strip() for s in (body.display_name, body.school, body.grade)):
        raise ValueError("Provide a pseudonym, school, grade and consent confirmation")
    learner_id = "L-" + uuid.uuid4().hex[:12]
    with db(True) as connection:
        connection.execute("INSERT INTO learners VALUES(?,?,?,?,?,?,?)", (
            learner_id, body.display_name.strip(), body.school.strip(), body.grade.strip(), actor["id"], 1, 1))
        audit(connection, actor["id"], "human_create_learner", body.model_dump(), {"learner_id": learner_id})
    return {"learner_id": learner_id}


@app.get("/api/learners/{learner_id}")
def learner(learner_id: str, actor=Depends(teacher)):
    with db() as connection:
        info = assigned(connection, learner_id, actor)
        bundle = evidence.get_evidence(connection, learner_id)
        profiles = [dict(r) for r in connection.execute(
            "SELECT * FROM profiles WHERE learner_id=? ORDER BY created_at DESC", (learner_id,))]
        for profile in profiles:
            profile["content"] = json.loads(profile["content"])
        runs = [dict(r) for r in connection.execute(
            "SELECT * FROM runs WHERE learner_id=? ORDER BY started_at DESC LIMIT 10", (learner_id,))]
        return {"learner": info, **bundle, "profiles": profiles, "runs": runs}


class RunRequest(BaseModel):
    provider: str = "local"


async def background_run(run_id):
    async with run_lock:
        try:
            await execute_run(run_id)
        except Exception:
            pass  # execute_run persists the failure and action trace for the teacher.


@app.post("/api/learners/{learner_id}/runs")
async def start_run(learner_id: str, body: RunRequest, actor=Depends(teacher)):
    if body.provider not in {"local", "gemini"}:
        raise ValueError("Select local or gemini")
    if body.provider == "gemini" and not os.environ.get("GEMINI_API_KEY"):
        raise ValueError("Configure GEMINI_API_KEY before choosing Gemini")
    with db() as connection:
        assigned(connection, learner_id, actor)
    try:
        run_id = create_run(learner_id, actor["id"], body.provider)
    except sqlite3.IntegrityError:
        raise HTTPException(409, "This learner already has an active run")
    task = asyncio.create_task(background_run(run_id))
    tasks.add(task)
    task.add_done_callback(tasks.discard)
    return {"run_id": run_id}


@app.get("/api/runs/{run_id}")
def run_details(run_id: str, actor=Depends(teacher)):
    with db() as connection:
        row = connection.execute("SELECT * FROM runs WHERE id=? AND teacher_id=?", (run_id, actor["id"])).fetchone()
        if row is None:
            raise HTTPException(404, "Run not found")
        events = [dict(e) for e in connection.execute("SELECT * FROM audit WHERE run_id=? ORDER BY id", (run_id,))]
        for event in events:
            event["inputs"] = json.loads(event["inputs"])
            event["outputs"] = json.loads(event["outputs"])
        return {"run": dict(row), "events": events}


class Review(BaseModel):
    content_hash: str
    decision: str
    note: str = Field(min_length=1, max_length=2000)
    guardian_conversation_confirmed: bool = False


@app.post("/api/profiles/{profile_id}/review")
def review(profile_id: str, body: Review, actor=Depends(teacher)):
    with db(True) as connection:
        return evidence.review(connection, profile_id, actor["id"], body.content_hash, body.decision,
                               body.note, body.guardian_conversation_confirmed)


@app.get("/api/profiles/{profile_id}/report")
def report(profile_id: str, actor=Depends(teacher)):
    with db(True) as connection:
        row = connection.execute("SELECT * FROM profiles WHERE id=?", (profile_id,)).fetchone()
        if row is None:
            raise HTTPException(404, "Profile not found")
        learner = assigned(connection, row["learner_id"], actor)
        if row["state"] != "released" or row["evidence_revision"] != learner["revision"]:
            raise HTTPException(403, "A current, approved and released profile is required")
        profile = json.loads(row["content"])
        if profile["policy_hash"] != digest(evidence.POLICY):
            raise HTTPException(403, "The rubric has changed. Generate a fresh profile.")
        text = f"# {learner['display_name']} — assessment review\n\n{learner['school']}\n\n"
        for finding in profile["findings"]:
            text += finding["statement"] + "\n\nEvidence: " + ", ".join(finding["evidence_ids"]) + "\n\n"
        text += "\n".join(profile["caveats"]) + f"\n\nReviewed by {actor['name']}.\n"
        text += "\n## Source record details\n\n"
        cited = {source for finding in profile["findings"] for source in finding["evidence_ids"]}
        for source in evidence.get_evidence(connection, learner["id"])["evidence"]:
            if source["id"] in cited:
                text += (f"- {source['id']} | {source['observed_at']} | {source['title']} | "
                         f"{source['score']:g}/{source['maximum']:g} | {source['source']}\n")
        audit(connection, actor["id"], "download_released_report", {"profile_id": profile_id},
              {"state": "released"}, row["run_id"])
    return PlainTextResponse(text, headers={"Content-Disposition": f'attachment; filename="learner-{learner["id"]}-review.md"'})


class EvidenceImport(BaseModel):
    consent_confirmed: bool
    records: list[dict]


@app.post("/api/learners/{learner_id}/evidence")
def import_records(learner_id: str, body: EvidenceImport, actor=Depends(teacher)):
    if not body.consent_confirmed:
        raise ValueError("Confirm consent for the records before importing")
    with db(True) as connection:
        assigned(connection, learner_id, actor)
        return evidence.import_evidence(connection, learner_id, body.records, actor["id"])


class EvidenceCorrection(BaseModel):
    record: dict
    expected_revision: int
    reason: str = Field(min_length=1, max_length=2000)
    consent_confirmed: bool


@app.post("/api/learners/{learner_id}/correction")
def correct_record(learner_id: str, body: EvidenceCorrection, actor=Depends(teacher)):
    if not body.consent_confirmed:
        raise ValueError("Confirm consent before correcting evidence")
    with db(True) as connection:
        assigned(connection, learner_id, actor)
        return evidence.correct_evidence(connection, learner_id, body.record, actor["id"],
                                         body.expected_revision, body.reason)


class MoodleItem(BaseModel):
    item_id: int = Field(gt=0)
    skill: str
    observed_at: date


class MoodleImport(BaseModel):
    consent_confirmed: bool
    user_id: int = Field(gt=0)
    course_id: int = Field(gt=0)
    academic_year: int = Field(ge=2000, le=2100)
    term: int = Field(ge=1, le=3)
    items: list[MoodleItem] = Field(min_length=1, max_length=100)


@app.post("/api/learners/{learner_id}/moodle")
async def import_moodle(learner_id: str, body: MoodleImport, actor=Depends(teacher)):
    if not body.consent_confirmed:
        raise ValueError("Confirm consent before accessing learner records")
    with db(True) as connection:
        assigned(connection, learner_id, actor)
        audit(connection, actor["id"], "moodle_import_request",
              {"learner_id": learner_id, "course_id": body.course_id, "user_id": body.user_id},
              {"status": "started"})
    rows = await fetch_mapped_grades(learner_id, body.user_id, body.course_id, body.academic_year, body.term,
                                   [item.model_dump(mode="json") for item in body.items])
    with db(True) as connection:
        return evidence.import_evidence(connection, learner_id, rows, actor["id"])


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/")
def home():
    return FileResponse(ROOT / "studio" / "static" / "index.html")


app.mount("/static", StaticFiles(directory=ROOT / "studio" / "static"), name="static")
