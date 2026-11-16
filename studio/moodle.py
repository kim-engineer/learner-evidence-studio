"""Import explicitly mapped assessment items through Moodle's user-grade report API."""
import os
import hashlib
from datetime import datetime, timezone
from urllib.parse import urlparse

import httpx


async def fetch_mapped_grades(learner_id, user_id, course_id, academic_year, term, items):
    base = os.environ.get("MOODLE_URL", "").rstrip("/")
    token = os.environ.get("MOODLE_TOKEN", "")
    site_id = hashlib.sha256(base.encode()).hexdigest()[:12]
    if urlparse(base).scheme != "https" or not token:
        raise ValueError("Configure an HTTPS MOODLE_URL and a restricted MOODLE_TOKEN on the server")
    if not items or len(items) > 100:
        raise ValueError("Map between 1 and 100 grade-item IDs to skill tags")
    async with httpx.AsyncClient(timeout=30, follow_redirects=False) as client:
        response = await client.post(base + "/webservice/rest/server.php", data={
            "wstoken": token, "wsfunction": "gradereport_user_get_grade_items",
            "moodlewsrestformat": "json", "courseid": course_id, "userid": user_id,
        })
    if response.status_code != 200:
        raise ValueError(f"Moodle returned HTTP {response.status_code}")
    data = response.json()
    if "exception" in data:
        raise ValueError("Moodle rejected the grade request. Check service permissions and identifiers.")
    reports = [r for r in data.get("usergrades", []) if int(r["userid"]) == user_id]
    if len(reports) != 1:
        raise ValueError("Moodle did not return the requested learner's grade report")
    mappings = {int(item["item_id"]): item for item in items}
    if len(mappings) != len(items):
        raise ValueError("Map each grade item only once")
    rows = []
    for item in reports[0].get("gradeitems", []):
        mapping = mappings.get(int(item["id"]))
        if not mapping or item.get("graderaw") is None or item.get("itemtype") != "mod":
            continue
        if item.get("scaleid") or item.get("gradeishidden") or item.get("gradehiddenbydate") or item.get("gradeneedsupdate"):
            raise ValueError("Import visible, current numeric grades only. Ordinal scales need a reviewed conversion.")
        low, high = float(item["grademin"]), float(item["grademax"])
        if high <= low:
            raise ValueError("This grade item needs a numeric scale with a positive range")
        observed_at = mapping["observed_at"]
        timestamp = int(item.get("gradedategraded") or item.get("gradedatesubmitted") or 0)
        recorded_at = datetime.fromtimestamp(timestamp, timezone.utc).date().isoformat() if timestamp else observed_at
        recorded_at = max(recorded_at, observed_at)
        rows.append({
            "id": f"moodle-{site_id}-{course_id}-{user_id}-{item['id']}",
            "kind": "assessment", "skill": mapping["skill"], "academic_year": academic_year,
            "term": term, "observed_at": observed_at, "recorded_at": recorded_at,
            "title": str(item.get("itemname") or f"Grade item {item['id']}")[:300],
            "score": round(float(item["graderaw"])-low, 6), "maximum": round(high-low, 6),
            "note": "Skill and assessment date mapped by the importing teacher.",
            "source": f"moodle:{site_id}:course/{course_id}/user/{user_id}/gradeitem/{item['id']}",
            "reliable": True,
        })
    if len(rows) != len(mappings):
        raise ValueError("Some mapped items are missing, ungraded, or are totals. Import explicit graded activity items.")
    return rows
