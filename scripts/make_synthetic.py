"""Build the disclosed synthetic cohort without real learner records."""
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
learners = [{"id": f"L00{i}", "display_name": f"Learner {letter}"} for i, letter in enumerate("ABCD", 1)]
terms = [(2024, 2), (2024, 3), (2025, 1), (2025, 2), (2025, 3), (2026, 1)]
series = {
    "L001": {"reading_comprehension": [38, 42, 51, 58, 68, 76], "spatial_reasoning": [74, 78, 80, 76, 82, 85]},
    "L002": {"reading_comprehension": [42, 39, 43, 38, 41, 44], "spatial_reasoning": [50, 82, 41, 77, 49, 71]},
    "L003": {"reading_comprehension": [None, None, None, None, 60, 80], "spatial_reasoning": [None, None, None, None, 48, 73]},
    "L004": {"reading_comprehension": [60, 59, 63, 62, 61, 65], "spatial_reasoning": [90, 89, 40, 42, 39, 41]},
}
rows = []
for learner, skills in series.items():
    for skill, values in skills.items():
        for index, ((year, term), score) in enumerate(zip(terms, values)):
            if score is None:
                continue
            for attempt in range(2):
                day = 10 + attempt * 8
                month = term * 3
                observed = f"{year}-{month:02}-{day:02}"
                rows.append({
                    "id": f"{learner}-{skill[:3]}-{year}-{term}-{attempt}",
                    "learner_id": learner, "kind": "assessment", "skill": skill,
                    "academic_year": year, "term": term, "observed_at": observed,
                    "recorded_at": f"{year}-{month:02}-28", "title": f"{skill.replace('_',' ').title()} task {attempt+1}",
                    "score": max(0, score - attempt * 4), "maximum": 100,
                    "note": "", "source": f"synthetic://{learner}/{year}/T{term}/{skill}/{attempt}", "reliable": True,
                })
rows.extend([
    {"id":"L001-note-1","learner_id":"L001","kind":"observation","skill":"reading_comprehension","academic_year":2026,
     "term":1,"observed_at":"2026-03-20","recorded_at":"2026-04-12","title":"Teacher observation",
     "score":None,"maximum":None,"note":"Asked for extra time to reread the passage. Late entry from a paper notebook.",
     "source":"synthetic://teacher-notes/late-entry-1","reliable":True},
    {"id":"L001-uncertain-1","learner_id":"L001","kind":"assessment","skill":"reading_comprehension","academic_year":2026,
     "term":1,"observed_at":"2026-03-22","recorded_at":"2026-03-23","title":"Unclear handwritten mark",
     "score":98,"maximum":100,"note":"Digit may be 38 or 98. Teacher verification pending.",
     "source":"synthetic://paper-register/uncertain","reliable":False},
])
(root/"data"/"synthetic.json").write_text(json.dumps({"synthetic":True,"learners":learners,"evidence":rows},indent=2))
print(f"Generated {len(rows)} disclosed synthetic observations")
