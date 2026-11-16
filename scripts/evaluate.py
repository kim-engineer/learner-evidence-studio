"""Run real open-weights evaluations and export synthetic audit evidence."""
import argparse
import asyncio
import json
import os
import platform
import tempfile
import time
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="evaluation/reproduced")
    args = parser.parse_args()
    output = Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="learner-eval-") as temporary:
        os.environ["STUDIO_DATA_DIR"] = temporary
        from studio.agent import create_run, execute_run
        from studio.store import initialise, db, now
        from studio.model import MODEL_ID, MODEL_REVISION
        initialise()
        results = []
        async def run_suite():
            for index, learner in enumerate(["L001","L001","L001","L002","L003","L004"], 1):
                started = time.monotonic()
                run_id = create_run(learner, "demo.teacher")
                try:
                    await execute_run(run_id)
                except Exception as exc:
                    print("FAILED", learner, str(exc), flush=True)
                with db() as connection:
                    run = dict(connection.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone())
                    events = [dict(row) for row in connection.execute("SELECT * FROM audit WHERE run_id=? ORDER BY id", (run_id,))]
                    for event in events:
                        event["inputs"] = json.loads(event["inputs"])
                        event["outputs"] = json.loads(event["outputs"])
                    row = connection.execute("SELECT * FROM profiles WHERE run_id=?", (run_id,)).fetchone()
                    profile = dict(row) if row else None
                    if profile:
                        profile["content"] = json.loads(profile["content"])
                name = f"run-{index:02d}-{learner}.json"
                (output/name).write_text(json.dumps({"run":run,"events":events,"profile":profile},indent=2),encoding="utf-8")
                result = {"trial":index,"learner_id":learner,"run_id":run_id,"status":run["status"],
                          "duration_seconds":round(time.monotonic()-started,2),"model_calls":run["model_calls"],
                          "input_tokens":run["input_tokens"],"output_tokens":run["output_tokens"],
                          "content_hash":profile["content_hash"] if profile else None,"trace":name,
                          "lens":profile["content"]["lens"] if profile else None,
                          "findings":{f["skill"]:f["kind"] for f in profile["content"]["findings"]} if profile else {}}
                results.append(result)
                print(json.dumps(result),flush=True)
        asyncio.run(run_suite())
        summary = {"recorded_at":now(),"model":MODEL_ID,"revision":MODEL_REVISION,
                   "python":platform.python_version(),"platform":platform.platform(),
                   "execution":"real CPU open-weights model + two real stdio MCP servers",
                   "api_cost_usd_per_run":0,"compute_energy_cost":"not measured",
                   "results":results,"repeat_L001_identical":len({r["content_hash"] for r in results[:3]})==1}
        (output/"summary.json").write_text(json.dumps(summary,indent=2),encoding="utf-8")
        if any(r["status"] != "completed" for r in results):
            raise SystemExit(1)


if __name__ == "__main__":
    main()
