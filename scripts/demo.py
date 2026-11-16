"""Record a real synthetic local-model run as a timed terminal session and JSON."""
import asyncio
import json
import os
from pathlib import Path
import tempfile
import time


async def record(folder):
    from studio.agent import create_run, execute_run
    from studio.store import initialise, db, now
    initialise()
    start = time.monotonic()
    with (folder/"agent-run.cast").open("w",encoding="utf-8") as cast:
        cast.write(json.dumps({"version":2,"width":116,"height":36,"timestamp":int(time.time()),
                              "title":"Learner Evidence Studio — real open-weights task"})+"\n")
        def line(text):
            print(text,flush=True)
            cast.write(json.dumps([round(time.monotonic()-start,3),"o",text+"\r\n"])+"\n")
            cast.flush()
        line("LEARNER EVIDENCE STUDIO | Longitudinal strength tracking")
        line("Actual CPU model run | Synthetic learner L001 | 6 terms across 2024-2026")
        line("Qwen2.5-0.5B-Instruct + LangGraph + original learner MCP + borrowed filesystem MCP")
        line("Task: inspect evidence, check patterns, validate citations, save a draft for a teacher.")
        line("Loading the local model. No API key is used.")
        run_id = create_run("L001","demo.teacher")
        task = asyncio.create_task(execute_run(run_id))
        last = 0
        while True:
            with db() as connection:
                rows = connection.execute("SELECT * FROM audit WHERE run_id=? AND id>? ORDER BY id",(run_id,last)).fetchall()
            for event in rows:
                last = event["id"]
                action = event["action"]
                result = json.loads(event["outputs"])
                args = json.loads(event["inputs"])
                stamp = f"{time.monotonic()-start:05.1f}s"
                if action == "model_plan":
                    line(f"{stamp} PLAN -> {result['decision']['action']} (real model output)")
                elif action.endswith(".request"):
                    line(f"{stamp} CALL {action.removesuffix('.request')}")
                    small = {k:v for k,v in args.items() if k not in {'draft','policy','path'}}
                    if small:
                        line("         IN  " + json.dumps(small))
                elif action == "get_learner_evidence":
                    line(f"{stamp} OUT  {result['term_count']} terms / {len(result['evidence'])} source records / {result['scope']}")
                elif action == "assess_longitudinal_patterns":
                    line(f"{stamp} OUT  {result['lens']} lens: " + ", ".join(f["kind"] for f in result["findings"]))
                elif action == "validate_learner_profile":
                    line(f"{stamp} CHECK {'PASS' if result['valid'] else 'RETURN FOR ANOTHER CHECK'}")
                    for error in result["errors"]:
                        line("         " + error)
                elif action == "save_profile_draft":
                    line(f"{stamp} WRITE draft saved -> {result['state']}")
                elif action == "reference.read_text_file":
                    line(f"{stamp} OUT  reviewed school rubric read through borrowed MCP")
                elif action == "mcp_discover":
                    line(f"{stamp} MCP  {args['server']}: {len(result['tools'])} tools discovered")
            if task.done():
                await task
                break
            await asyncio.sleep(.15)
        with db() as connection:
            run = dict(connection.execute("SELECT * FROM runs WHERE id=?",(run_id,)).fetchone())
            profile = dict(connection.execute("SELECT * FROM profiles WHERE run_id=?",(run_id,)).fetchone())
            profile["content"] = json.loads(profile["content"])
            events = [dict(e) for e in connection.execute("SELECT * FROM audit WHERE run_id=? ORDER BY id",(run_id,))]
            for e in events:
                e["inputs"]=json.loads(e["inputs"])
                e["outputs"]=json.loads(e["outputs"])
        line("")
        for finding in profile["content"]["findings"]:
            line(f"FINDING  {finding['statement']}")
            line(f"SOURCES  {len(finding['evidence_ids'])} exact source IDs; first: {finding['evidence_ids'][0]}")
        line("")
        line("PAUSED FOR TEACHER | Draft cannot be downloaded as a released report yet.")
        line("Approval and a confirmed guardian conversation are separate authenticated actions.")
        line("KNOWN LIMITATION | Different assessment difficulty can mimic skill change.")
        line("The system cannot calibrate that effect. Source comparison remains a teacher's task.")
        line(f"COMPLETE | {run['model_calls']} model calls | {run['input_tokens']} input / {run['output_tokens']} output tokens")
        line("API COST $0 | Local electricity cost not measured | Full trace accompanies this recording.")
        await asyncio.sleep(8)
        line("END OF CONTINUOUS RECORDING")
        (folder/"agent-run.json").write_text(json.dumps({"run":run,"profile":profile,"events":events},indent=2),encoding="utf-8")
        (folder/"recording-info.json").write_text(json.dumps({"recorded_at":now(),"duration_seconds":round(time.monotonic()-start,2),
            "kind":"continuous timestamped terminal capture rendered without speed changes or cuts",
            "model":"Qwen/Qwen2.5-0.5B-Instruct","run_id":run_id,"synthetic_data":True,"human_approval_simulated":False},indent=2),encoding="utf-8")


if __name__ == "__main__":
    folder = Path("evaluation/demo").resolve()
    folder.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="learner-demo-") as temporary:
        os.environ["STUDIO_DATA_DIR"] = temporary
        asyncio.run(record(folder))
