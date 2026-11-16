"""Cited, bounded observations about assessment history and review-safe persistence."""
import json
import math
import uuid
from collections import defaultdict
from datetime import date

from .store import ROOT, audit, digest, encode, learner_record, now

POLICY = json.loads((ROOT / "reference" / "policy.json").read_text())
SKILLS = {"reading_comprehension", "spatial_reasoning", "numeracy", "scientific_reasoning", "writing"}
KINDS = {"assessment", "observation", "attendance"}


def get_evidence(connection, learner_id, scope="all"):
    learner = learner_record(connection, learner_id)
    rows = [dict(r) for r in connection.execute(
        "SELECT * FROM evidence WHERE learner_id=? ORDER BY academic_year,term,observed_at,id", (learner_id,))]
    periods = sorted({(r["academic_year"], r["term"]) for r in rows})
    if scope == "recent":
        periods = periods[-2:]
        rows = [r for r in rows if (r["academic_year"], r["term"]) in periods]
    elif scope != "all":
        raise ValueError("Scope must be recent or all")
    return {"learner_id": learner_id, "revision": learner["revision"], "scope": scope,
            "term_count": len(periods), "year_count": len({y for y, _ in periods}), "evidence": rows}


def assess(connection, learner_id, scope, lens, policy):
    if policy != POLICY:
        raise ValueError("The supplied rubric differs from the reviewed school rubric")
    if lens not in {"trajectory", "consistency"}:
        raise ValueError("Choose trajectory or consistency")
    bundle = get_evidence(connection, learner_id, scope)
    by_skill = defaultdict(list)
    excluded = []
    for row in bundle["evidence"]:
        if row["kind"] != "assessment":
            continue
        if not row["reliable"] or row["score"] is None:
            excluded.append(row["id"])
            continue
        by_skill[row["skill"]].append(row)
    findings = []
    for skill, rows in sorted(by_skill.items()):
        terms = defaultdict(list)
        for row in rows:
            terms[(row["academic_year"], row["term"])].append(100 * row["score"] / row["maximum"])
        trend = [{"year": year, "term": term, "percent": round(sum(scores) / len(scores), 1)}
                 for (year, term), scores in sorted(terms.items())]
        scores = [t["percent"] for t in trend]
        label = skill.replace("_", " ")
        span = f"{len(trend)} terms"
        change = round(scores[-1] - scores[0], 1)
        adequate = len(trend) >= policy["minimum_terms"] and len(rows) >= policy["minimum_assessments"]
        kind = "mixed"
        statement = (f"Recorded {label} assessment averages were between {min(scores):g}% and {max(scores):g}% "
                     f"across {span}. They do not meet the rubric's sustained high or low thresholds.")
        if not adequate:
            kind = "insufficient"
            statement = f"Only {len(trend)} terms of reliable {label} assessments are available. A sustained pattern is not established."
        elif lens == "trajectory" and abs(change) >= policy["improvement_points"]:
            kind = "improving" if change > 0 else "declining"
            direction = "increased" if change > 0 else "decreased"
            statement = (f"Recorded {label} assessment averages {direction} from {scores[0]:g}% to "
                         f"{scores[-1]:g}% across {span}. Assessment difficulty may differ between terms.")
        elif all(score >= policy["strength_floor"] for score in scores):
            kind = "consistent_strength"
            statement = f"Recorded {label} assessment averages stayed at or above {policy['strength_floor']}% across {span}."
        elif all(score <= policy["support_ceiling"] for score in scores):
            kind = "persistent_support"
            statement = (f"Recorded {label} assessment averages stayed at or below {policy['support_ceiling']}% "
                         f"across {span}. Review the source work with the learner to plan support.")
        findings.append({
            "skill": skill, "kind": kind, "statement": statement,
            "evidence_ids": [r["id"] for r in rows], "trend": trend,
        })
    caveats = [
        "These observations describe the supplied assessments and their recorded skill tags.",
        "Different assessment difficulty, missing records and changes in teaching may affect comparisons.",
        "Teachers determine appropriate support through discussion with the learner and guardian.",
    ]
    if excluded:
        caveats.append(f"{len(excluded)} uncertain or unscored assessment records were excluded.")
    return {
        "learner_id": learner_id, "evidence_revision": bundle["revision"],
        "scope": scope, "lens": lens, "policy_version": policy["version"],
        "policy_hash": digest(policy), "findings": findings, "excluded_ids": excluded,
        "context_ids": [r["id"] for r in bundle["evidence"] if r["kind"] != "assessment"],
        "caveats": caveats,
    }


def validate(connection, learner_id, draft):
    expected = assess(connection, learner_id, draft.get("scope"), draft.get("lens"), POLICY)
    errors = []
    if draft != expected:
        errors.append("The draft differs from recomputed source-supported observations")
    if draft.get("scope") != "all":
        errors.append("Review the complete available history before saving")
    needs_trajectory = draft.get("lens") == "consistency" and any(
        len(f["trend"]) >= POLICY["minimum_terms"] and
        abs(f["trend"][-1]["percent"] - f["trend"][0]["percent"]) >= POLICY["improvement_points"]
        for f in expected["findings"])
    if needs_trajectory:
        errors.append("Term results changed substantially. Check the trajectory lens before concluding.")
    return {"valid": not errors, "errors": errors, "content_hash": digest(expected),
            "revision": expected["evidence_revision"], "needs_trajectory": needs_trajectory}


def save_draft(connection, learner_id, run_id, draft):
    validation = validate(connection, learner_id, draft)
    if not validation["valid"]:
        raise ValueError("; ".join(validation["errors"]))
    existing = connection.execute("SELECT id,content_hash FROM profiles WHERE run_id=?", (run_id,)).fetchone()
    if existing:
        if existing["content_hash"] != digest(draft):
            raise ValueError("A different draft already exists for this run")
        return {"profile_id": existing["id"], "state": "pending_review", "reused": True}
    profile_id = uuid.uuid4().hex
    connection.execute("""INSERT INTO profiles
        (id,learner_id,run_id,evidence_revision,content,content_hash,state,created_at)
        VALUES(?,?,?,?,?,?,'pending_review',?)""",
        (profile_id, learner_id, run_id, draft["evidence_revision"], encode(draft), digest(draft), now()))
    return {"profile_id": profile_id, "state": "pending_review", "reused": False}


def import_evidence(connection, learner_id, rows, actor):
    learner = learner_record(connection, learner_id)
    if learner["teacher_id"] != actor:
        raise ValueError("This learner is outside the teacher's assignment")
    if not rows or len(rows) > 1000:
        raise ValueError("Import between 1 and 1000 evidence records")
    inserted = 0
    for row in rows:
        required = {"id", "kind", "skill", "academic_year", "term", "observed_at", "recorded_at",
                    "title", "score", "maximum", "note", "source", "reliable"}
        if set(row) != required:
            raise ValueError("Evidence fields do not match the documented import schema")
        if not isinstance(row["kind"], str) or not isinstance(row["skill"], str) or row["kind"] not in KINDS or row["skill"] not in SKILLS:
            raise ValueError("Unknown evidence kind or skill tag")
        if type(row["academic_year"]) is not int or not 2000 <= row["academic_year"] <= 2100:
            raise ValueError("Invalid academic year")
        if type(row["term"]) is not int or row["term"] not in (1, 2, 3):
            raise ValueError("Term must be 1, 2 or 3")
        if not isinstance(row["observed_at"], str) or not isinstance(row["recorded_at"], str):
            raise ValueError("Dates must be ISO date strings")
        observed = date.fromisoformat(row["observed_at"])
        recorded = date.fromisoformat(row["recorded_at"])
        if recorded < observed or observed > date.today() or recorded > date.today():
            raise ValueError("Dates must be ordered and cannot be in the future")
        if row["kind"] == "assessment" and row["score"] is not None:
            if type(row["score"]) not in (int, float) or type(row["maximum"]) not in (int, float):
                raise ValueError("Score and maximum must be JSON numbers")
            score, maximum = float(row["score"]), float(row["maximum"])
            if not math.isfinite(score) or not math.isfinite(maximum) or maximum <= 0 or not 0 <= score <= maximum:
                raise ValueError("Assessment score must be between zero and its positive maximum")
        elif row["score"] is not None or row["maximum"] is not None:
            raise ValueError("Context and unscored records must have null score and maximum")
        if not isinstance(row["reliable"], bool):
            raise ValueError("Reliable must be a boolean")
        for field, limit in [("id", 160), ("title", 300), ("note", 2000), ("source", 500)]:
            if not isinstance(row[field], str) or len(row[field]) > limit:
                raise ValueError(f"Invalid {field}")
        if not row["id"] or not row["source"]:
            raise ValueError("A stable evidence ID and source are required")
        old = connection.execute("SELECT * FROM evidence WHERE id=?", (row["id"],)).fetchone()
        values = {**row, "learner_id": learner_id, "reliable": int(row["reliable"])}
        if old:
            if dict(old) != values:
                raise ValueError("Evidence ID already exists with different content. Use the correction operation to replace it.")
            continue
        connection.execute("""INSERT INTO evidence
            (id,learner_id,kind,skill,academic_year,term,observed_at,recorded_at,title,score,maximum,note,source,reliable)
            VALUES(:id,:learner_id,:kind,:skill,:academic_year,:term,:observed_at,:recorded_at,
                   :title,:score,:maximum,:note,:source,:reliable)""", values)
        inserted += 1
    if inserted:
        connection.execute("UPDATE learners SET revision=revision+1 WHERE id=?", (learner_id,))
    audit(connection, actor, "import_evidence", {"learner_id": learner_id, "ids": [r["id"] for r in rows]},
          {"inserted": inserted, "duplicates": len(rows)-inserted})
    return {"inserted": inserted, "duplicates": len(rows)-inserted}


def correct_evidence(connection, learner_id, replacement, actor, expected_revision, reason):
    learner = learner_record(connection, learner_id)
    if learner["teacher_id"] != actor or learner["revision"] != expected_revision:
        raise ValueError("Assignment or evidence revision has changed. Refresh before correcting.")
    if not reason.strip():
        raise ValueError("Explain the correction")
    old = connection.execute("SELECT * FROM evidence WHERE id=? AND learner_id=?",
                             (replacement.get("id"), learner_id)).fetchone()
    if old is None:
        raise ValueError("The source to correct was not found")
    connection.execute("DELETE FROM evidence WHERE id=?", (old["id"],))
    result = import_evidence(connection, learner_id, [replacement], actor)
    audit(connection, actor, "human_correct_evidence",
          {"before": dict(old), "reason": reason, "expected_revision": expected_revision},
          {"after": replacement, "previous_profiles": "stale"})
    return result


def review(connection, profile_id, actor, content_hash, decision, note, conversation=False):
    row = connection.execute("""SELECT p.*,l.revision,l.teacher_id,l.consent
        FROM profiles p JOIN learners l ON l.id=p.learner_id WHERE p.id=?""", (profile_id,)).fetchone()
    if row is None or row["teacher_id"] != actor:
        raise ValueError("Profile not available to this teacher")
    if not row["consent"] or row["revision"] != row["evidence_revision"]:
        raise ValueError("Evidence or consent has changed. Generate a fresh draft.")
    if json.loads(row["content"])["policy_hash"] != digest(POLICY):
        raise ValueError("The rubric has changed. Generate a fresh draft.")
    if row["content_hash"] != content_hash:
        raise ValueError("The reviewed content hash does not match")
    if decision in {"approve", "reject"}:
        if row["state"] != "pending_review":
            raise ValueError("This draft has already been reviewed")
        if not note.strip():
            raise ValueError("Record a review note")
        state = "approved" if decision == "approve" else "rejected"
        connection.execute("""UPDATE profiles SET state=?,approved_by=?,approved_at=?,review_note=?
            WHERE id=?""", (state, actor, now(), note.strip(), profile_id))
    elif decision == "release":
        if row["state"] != "approved" or not conversation or not note.strip():
            raise ValueError("Release requires approval and a recorded teacher-guardian conversation")
        state = "released"
        connection.execute("UPDATE profiles SET state=?,released_by=?,released_at=? WHERE id=?",
                           (state, actor, now(), profile_id))
    else:
        raise ValueError("Unknown review action")
    audit(connection, actor, "human_" + decision,
          {"profile_id": profile_id, "content_hash": content_hash, "note": note,
           "guardian_conversation_confirmed": conversation}, {"state": state}, row["run_id"])
    return {"profile_id": profile_id, "state": state}
