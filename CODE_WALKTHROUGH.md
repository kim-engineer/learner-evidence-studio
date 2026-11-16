# Explain and extend the build

## A ten-minute walkthrough

1. **Problem and data (one minute).** Open `data/synthetic.json`. Explain that records belong to one learner and carry dates, skill tags, reliability and a stable source pointer. Show the uncertain score and short-history learner. These are intentionally fictional records.
2. **Evidence rules (two minutes).** Open `studio/evidence.py`. Follow `assess`: normalise scores, group by skill and term, calculate means, form bounded statements and collect exact source IDs. Explain why these observations cannot establish innate aptitude or cause. `validate` recomputes the entire expected draft and rejects tampering, short-scope conclusions and missed changes.
3. **MCP boundary (one minute).** Open `studio/mcp_server.py`. There are four distinct tools, including a draft write. The session's run ID binds tools to a learner. No agent tool can approve or release. The borrowed filesystem MCP server reads the reviewed rubric from a restricted read-only directory.
4. **Planning and recovery (two minutes).** Open `studio/agent.py`. Show the LangGraph plan/act loop and state-dependent options. The local model picks an action from permitted choices. The recorded L001 run chose a consistency lens; validation required a trajectory check before it could save. This is real feedback-driven replanning. The finite JSON grammar in `model.py` prevents invented tool names; it does not secretly select the action for the model.
5. **Human authority (one minute).** Trace `web.py` into `evidence.review`. A signed-in teacher approves an exact content hash at the current evidence revision. Report release requires another action confirming a guardian conversation. These confirmations are attestations by the teacher, not independent proof that a meeting happened.
6. **Verification and limitation (two minutes).** Open `EVALS.md`, a final-run JSON and `evaluation/demo/agent-demo.mp4`. Distinguish real model runs from mock provider tests. Show the unresolved difficulty-calibration task. Explain that Docker, live Gemini, live Moodle and school impact are not presented as tested.
7. **Ownership (one minute).** Explain which original application choices you directed, which libraries were borrowed and how AI assisted the implementation. Preserve their attribution.

## Likely live-review changes

| Request | Where to work | What must stay true |
| --- | --- | --- |
| Add a reviewed skill tag | `evidence.SKILLS`, fixtures, import guide | Sources and term grouping still match exactly |
| Change a demonstration threshold | `reference/policy.json`, relevant expected outcomes | Version the rubric; restart; regenerate drafts before approval |
| Add a fourth school term | Import validation, Moodle schema, fixtures | Ordering and minimum-history checks remain explicit |
| Add a source document URL | Source schema and source-dialog renderer | Do not render untrusted source HTML or expose credentials |
| Handle assessment difficulty | Add reviewed assessment-form metadata and calibration tests | Do not call raw percentage change a calibrated skill gain |
| Add another teacher | Account provisioning and learner-assignment model | Every HTTP action and MCP session remains scoped; test isolation |
| Add multilingual wording | Deterministic statement templates and UI strings | Citations, caveats and human approval survive translation |

## Decisions worth defending

- The model plans but does not invent findings. This makes a parent-facing “why?” answer reproducible from the records.
- A low-cost CPU model keeps local processing feasible; its limited planning choices are documented openly.
- Notes are context for the teacher, not an invitation for the model to infer personality or diagnose a child.
- The workflow makes no class leaderboard or automatic pathway choice.
- Corrections invalidate old drafts instead of silently changing already approved text.
- SQLite fits the local prototype. It is not a claim of multi-school production scalability.

Read and run the tests yourself before a technical review. Understanding the code and making your own classroom-informed changes are more defensible than claiming that no assistance was used.
