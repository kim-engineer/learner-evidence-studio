"""LangGraph planning, real MCP sessions, validation, recovery, and draft persistence."""
import asyncio
import json
import os
import sys
import uuid
from contextlib import AsyncExitStack
from typing import TypedDict

from langgraph.graph import END, START, StateGraph
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from .model import MODEL_ID, planner
from .store import ROOT, audit, db, now


class State(TypedDict, total=False):
    steps: int
    evidence: dict
    draft: dict
    validation: dict
    action: str
    error: str
    done: bool
    profile_id: str


def create_run(learner_id, teacher_id, provider="local"):
    run_id = uuid.uuid4().hex
    model = MODEL_ID if provider == "local" else os.environ.get("GEMINI_MODEL", "gemini-3.5-flash-lite")
    with db(True) as connection:
        connection.execute("""INSERT INTO runs
            (id,learner_id,teacher_id,status,provider,model,started_at) VALUES(?,?,?,'queued',?,?,?)""",
            (run_id, learner_id, teacher_id, provider, model, now()))
        audit(connection, teacher_id, "request_profile_review", {"learner_id": learner_id},
              {"run_id": run_id, "provider": provider}, run_id)
    return run_id


def options(state):
    if not state.get("evidence"):
        return ["get_recent", "get_all"]
    if not state.get("draft"):
        if state["evidence"]["scope"] == "recent":
            return ["get_all", "assess_trajectory", "assess_consistency"]
        return ["assess_trajectory", "assess_consistency"]
    if not state.get("validation"):
        return ["validate"]
    if not state["validation"]["valid"]:
        if state["evidence"]["scope"] == "all" and state["validation"].get("needs_trajectory"):
            return ["assess_trajectory"]
        return ["get_all"]
    return ["save"]


async def connect(stack, command, args, env):
    streams = await stack.enter_async_context(stdio_client(StdioServerParameters(command=command, args=args, env=env)))
    session = await stack.enter_async_context(ClientSession(*streams))
    await session.initialize()
    return session


async def execute_run(run_id, model_planner=None):
    chooser = model_planner or planner
    with db(True) as connection:
        run = dict(connection.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone())
        changed = connection.execute("UPDATE runs SET status='running' WHERE id=? AND status='queued'", (run_id,)).rowcount
        if changed != 1:
            raise ValueError("Run has already started")
    env = dict(os.environ, STUDIO_RUN_ID=run_id, PYTHONPATH=str(ROOT))
    filesystem = ROOT / "node_modules" / "@modelcontextprotocol" / "server-filesystem" / "dist" / "index.js"
    try:
        async with AsyncExitStack() as stack:
            own = await connect(stack, sys.executable, ["-m", "studio.mcp_server"], env)
            reference = await connect(stack, "node", [str(filesystem), "--read-only", str(ROOT/"reference")], env)
            for label, session in [("learner", own), ("reference", reference)]:
                listing = await session.list_tools()
                with db(True) as connection:
                    audit(connection, "agent", "mcp_discover", {"server": label},
                          {"tools": [t.name for t in listing.tools]}, run_id)
            refargs = {"path": str(ROOT/"reference"/"policy.json")}
            with db(True) as connection:
                audit(connection, "agent", "reference.read_text_file.request", refargs, {"status": "started"}, run_id)
            refresult = await reference.call_tool("read_text_file", refargs)
            if refresult.isError:
                raise RuntimeError("Reference MCP could not read the school rubric")
            policytext = "".join(c.text for c in refresult.content if c.type == "text")
            policy = json.loads(policytext)
            with db(True) as connection:
                audit(connection, "agent", "reference.read_text_file", refargs, policy, run_id)

            async def plan(state):
                observation = {}
                if state.get("evidence"):
                    bundle = state["evidence"]
                    observation = {"scope": bundle["scope"], "term_count": bundle["term_count"],
                                   "year_count": bundle["year_count"]}
                    scores = {}
                    for row in bundle["evidence"]:
                        if row["kind"] == "assessment" and row["reliable"] and row["score"] is not None:
                            scores.setdefault(row["skill"], []).append(round(100 * row["score"] / row["maximum"], 1))
                    observation["assessment_percentages_in_date_order"] = scores
                if state.get("draft"):
                    observation["findings"] = [{"skill": f["skill"], "kind": f["kind"]} for f in state["draft"]["findings"]]
                if state.get("validation"):
                    observation["validation"] = state["validation"]
                context = {"goal": "Review this learner's assessment history for sustained patterns and changes.",
                           "options": options(state), "observations": observation,
                           "previous_error": state.get("error", ""), "minimum_terms": policy["minimum_terms"]}
                decision, usage = await chooser.choose(context, run["provider"])
                with db(True) as connection:
                    audit(connection, "agent", "model_plan", context, {"decision": decision, "usage": usage}, run_id)
                    connection.execute("""UPDATE runs SET input_tokens=input_tokens+?,output_tokens=output_tokens+?,
                        model_calls=model_calls+1 WHERE id=?""",
                        (usage["input_tokens"], usage["output_tokens"], run_id))
                return {"action": decision["action"], "steps": state.get("steps", 0)+1,
                        "error": decision["reason"] if decision["action"] == "invalid" else ""}

            async def act(state):
                action = state["action"]
                if action == "invalid":
                    return {}
                args = {"learner_id": run["learner_id"]}
                if action.startswith("get_"):
                    name = "get_learner_evidence"
                    args["scope"] = "recent" if action == "get_recent" else "all"
                elif action.startswith("assess_"):
                    name = "assess_longitudinal_patterns"
                    args.update(scope=state["evidence"]["scope"], lens=action.removeprefix("assess_"), policy=policy)
                elif action == "validate":
                    name = "validate_learner_profile"
                    args["draft"] = state["draft"]
                else:
                    name = "save_profile_draft"
                    args["draft"] = state["draft"]
                try:
                    with db(True) as connection:
                        audit(connection, "agent", name + ".request", args, {"status": "started"}, run_id)
                    result = await asyncio.wait_for(own.call_tool(name, args), timeout=30)
                    if result.isError:
                        raise ValueError(" ".join(c.text for c in result.content if c.type == "text"))
                    value = result.structuredContent
                    if value is None:
                        value = json.loads("".join(c.text for c in result.content if c.type == "text"))
                    if "result" in value and len(value) == 1:
                        value = value["result"]
                    if action.startswith("get_"):
                        return {"evidence": value, "draft": {}, "validation": {}, "error": ""}
                    if action.startswith("assess_"):
                        return {"draft": value, "validation": {}, "error": ""}
                    if action == "validate":
                        return {"validation": value, "error": ""}
                    return {"done": True, "profile_id": value["profile_id"], "error": ""}
                except (Exception, asyncio.TimeoutError) as exc:
                    with db(True) as connection:
                        audit(connection, "agent", "tool_recovery", {"tool": name, "step": state["steps"]},
                              {"error": str(exc)[:1000], "next": "replan"}, run_id, "error")
                    await asyncio.sleep(min(state["steps"], 3))
                    return {"error": str(exc)[:500]}

            def route(state):
                return END if state.get("done") or state["steps"] >= 12 else "plan"

            graph = StateGraph(State)
            graph.add_node("plan", plan)
            graph.add_node("act", act)
            graph.add_edge(START, "plan")
            graph.add_edge("plan", "act")
            graph.add_conditional_edges("act", route, {"plan": "plan", END: END})
            output = await graph.compile().ainvoke({"steps": 0, "done": False}, {"recursion_limit": 30})
            if not output.get("done"):
                raise RuntimeError("The agent reached its 12-step limit. " + output.get("error", "Review the trace and retry."))
            with db(True) as connection:
                connection.execute("UPDATE runs SET status='completed',finished_at=?,profile_id=? WHERE id=?",
                                   (now(), output["profile_id"], run_id))
                audit(connection, "agent", "run_completed", {}, {"profile_id": output["profile_id"]}, run_id)
            return output
    except BaseException as exc:
        with db(True) as connection:
            connection.execute("UPDATE runs SET status='failed',finished_at=?,error=? WHERE id=?",
                               (now(), str(exc)[:1500], run_id))
            audit(connection, "system", "run_failed", {}, {"error": str(exc)[:1500]}, run_id, "error")
        raise
