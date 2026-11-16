# Architecture — Learner Evidence Studio

**Scope:** one teacher reviews one learner's dated assessment history. The demonstration follows six terms across three calendar years. Sources are synthetic JSON or explicitly mapped Moodle grade items. No cohort ranking or pathway assignment exists.

The teacher requests a review through FastAPI. LangGraph coordinates the model and two MCP servers, saves a validated draft, then hands control back to authenticated teacher actions.

**Agent shape.** `studio/agent.py` uses LangGraph `StateGraph` with plan/act nodes and conditional continuation. The real model chooses recent versus complete evidence and a consistency versus trajectory analysis. After each result, its next choices reflect observed state. Validation rejects incomplete history, altered citations and consistency-only reviews that omit large changes. The planner then requests further evidence or a trajectory check. Twelve steps bound the run. Errors are recorded and return to planning; a server restart marks interrupted runs failed for an explicit retry.

**Model boundary.** Qwen2.5-0.5B-Instruct runs locally through Transformers. A finite JSON grammar constrains output syntax while model logits select an allowed action. This is bounded model planning, not free-form tool arguments. Gemini uses native `generateContent` with a JSON action schema. Only trusted numeric summaries and skill tags enter model context. Calculations and sourced statements are deterministic domain code, not unconstrained model assertions.

| MCP server | Tools / role |
| --- | --- |
| Built: `studio/mcp_server.py` | `get_learner_evidence`, `assess_longitudinal_patterns`, `validate_learner_profile`, `save_profile_draft` |
| Borrowed: official `@modelcontextprotocol/server-filesystem` 2.3.0 | Actual `read_text_file` call for the rubric; `--read-only`, restricted to `reference/` |

The official filesystem server supplies a maintained MCP implementation and directory boundaries instead of another homemade file tool. Each custom session is restricted to its persisted run's learner. Saving is an idempotent draft write; no MCP tool can approve, release or send a report.

**Persistence and people.** SQLite transactions store evidence revisions, immutable draft contents, hashes and timestamped inputs/outputs. Authenticated teacher HTTP actions approve or reject the exact hash. A second action records the guardian-conversation confirmation before enabling report download. Corrections preserve before/after audit data and invalidate previous approvals for export. Sessions use hashed tokens, CSRF checking and same-origin writes. The audit trail is append-only through application code, not tamper-proof against the database owner.

**Deployment.** FastAPI serves the responsive plain-JavaScript interface. One process queues model runs to fit a small CPU host. Model weights are downloaded once, then cached. The local launcher is verified; Docker and live Moodle/Gemini deployment remain unverified. See `EVALS.md` for measurements and limitations.
