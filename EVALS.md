# Evaluations — 12 November 2026

## What actually ran

The final verification executed **23 passing tests and one expected failure** on CPython 3.12 / Linux x86_64. `evaluation/unit-results.xml` is the machine-readable pytest output. The expected failure is an unimplemented capability, not a hidden passing result. Provider contract tests use mocks and are explicitly distinguished from live inference.

Six additional evaluations ran the real **Qwen2.5-0.5B-Instruct** weights on CPU through LangGraph and two actual stdio MCP servers. Their complete inputs, outputs and timestamps are in `evaluation/final-runs/`. No Gemini key or live Moodle token was available. `evaluation/ui-results.json` records JavaScript DOM integration against a real local HTTP server and another real local-model task. `evaluation/bootstrap-results.json` records a successful `python run.py` start from a fresh virtual environment.

## Tasks and outcomes

| Task | Result | Evidence / interpretation |
| --- | --- | --- |
| Follow L001 reading across six terms and three years | PASS | Mean changed from 36% to 74%; 12 exact source IDs |
| Detect sustained spatial results and persistent reading-support observations | PASS | L001 spatial and L002 reading fixtures, checked against expected bounds |
| Refuse a sustained-pattern claim with only two terms | PASS | L003 findings say insufficient history |
| Exclude uncertain handwriting and keep late notes as context | PASS | One uncertain score excluded; context note not scored |
| Reject altered statements and invented citations | PASS | Full source recomputation rejects both mutations |
| Reject a recent-only draft until the full available history is checked | PASS | Validation returns an explicit retry instruction |
| Catch a consistency-only view that omits a large change | PASS | Final real L001 run replans to trajectory after failed validation |
| Import unchanged IDs twice without duplicates | PASS | Existing row skipped; revision unchanged |
| Roll back a partly invalid import batch | PASS | No partial inserted row survives |
| Retry a draft save without creating another profile | PASS | Same persisted profile ID returned |
| Require teacher approval and a conversation confirmation before release | PASS | Premature release rejected; named actor and hash logged |
| Correct a source without double counting; invalidate old approval | PASS | One current assessment remains; before/after correction logged |
| Reject another teacher's access and processing without consent | PASS | Domain guards reject the requests |
| Reject approval under a changed rubric | PASS | Stored rubric hash no longer matches current policy |
| Avoid claiming variation for constant midrange scores | PASS | All term averages remain accurately described as 60% |
| Treat malicious note instructions as source data | PASS | Text remains context; no ranking or release follows |
| Call Gemini using its native API/header/structured-output contract | PASS, mocked | No live cloud generation or billing verified |
| Map a Moodle numeric grade and retain a stable source ID | PASS, mocked | Source reviewed in Moodle 4.2/4.5; live instance untested |
| Reject ordinal scales, hidden grades and grades needing update | PASS, mocked | Three separate test cases |
| Enforce HTTP sign-in, CSRF and release-only downloads | PASS | Real application exercised with test HTTP client |
| Discover both real MCP servers and recover from partial-history validation | PASS | Scripted test planner, actual MCP transport; not counted as a real-model trial |
| Prevent an MCP run from reading another learner | PASS | Actual stdio call returns an access error |
| Infer difficulty-calibrated skill growth from unequal assessments | **FAIL — unresolved** | No calibration data or calibrated estimator exists |

## Real model outcomes and variation

| Trial | Learner | Result | Model calls | Input / output tokens | Elapsed seconds |
| --- | --- | --- | --- | --- | --- |
| 1 | L001 | Reading increase; sustained spatial results | 7 | 2571 / 49 | 29.76 |
| 2 | L001 | Same profile hash | 7 | 2571 / 49 | 14.58 |
| 3 | L001 | Same profile hash | 7 | 2571 / 49 | 14.48 |
| 4 | L002 | Persistent reading-support observation; spatial endpoints increased | 7 | 2570 / 49 | 11.34 |
| 5 | L003 | Insufficient history for both skills | 5 | 1396 / 35 | 7.12 |
| 6 | L004 | Mixed reading results; spatial results decreased | 7 | 2571 / 49 | 13.96 |

All six completed a draft write. Three repeated L001 trials had **zero profile-hash variation** under greedy constrained decoding. Timing varied with model loading and host contention; these results do not establish performance on a low-powered school computer. L002's spatial scores fluctuate considerably even though the first-to-last change is positive. The statement describes endpoints and displays intermediate terms; it must not be presented as steady improvement.

Each local run incurred **$0 in model API fees**. CPU, electricity, download and hosting costs are not measured and are not claimed to be zero. Gemini usage accounting is implemented, but no live cost measurement exists. See `summary.json` for the exact model revision and environment.

## Failure and recovery evidence

The first development planner produced an invented tool name and exhausted its 12-step limit. Its original trace is retained as `evaluation/development/initial-planner-failure.json`. Finite JSON action decoding fixed that syntax/choice failure. A later consistency-only review missed large changes; source validation now requires a trajectory check. The final real trace and demo show that feedback and recovery. No failed development result is presented as a successful final run.

**Failure left unfixed:** raw quiz percentages cannot distinguish easier tests from actual skill growth. The explicit pytest expected failure requests `difficulty_adjusted_growth`, which the system does not provide. Next, collect consented, teacher-reviewed assessment-form metadata and anchor items, evaluate a calibrated approach, and test whether teacher judgements support the resulting comparisons. Until then, retain the caveat and human source review. Adding another prompt would not supply the missing measurement evidence.

## Interface and deployment limits

DOM integration passed sign-in, learner rendering, real agent activity, citation opening, empty-note rejection, approval, conversation gating, released download, new learner creation and HTML escaping. The test uses jsdom with a dialog shim. A real visual browser/layout/accessibility audit could not run in the available environment, so none is claimed. The terminal demo is a rendered timed capture, not a browser screen recording.

Docker execution, Windows execution, live Gemini, live Moodle, multi-user load, a teacher interview, real-school deployment and learning impact were **not tested in the 12 November build environment**. The application is a local prototype. Reproduce unit tests with `python -m pytest -q`, real inference with `python -m scripts.evaluate`, and DOM integration with `npm ci` followed by `python -m scripts.check_ui` inside the activated Python environment.

## Windows report — 15 November 2026

A subsequent user report showed successful Windows application startup, sign-in, learner listing, discovery of both MCP servers and reading of the reference rubric. The local Qwen review then remained in `running` status with zero completed model calls. No completed Windows review has been verified.

The trace ends before the first `model_plan` event. That event is written only after the planner returns, so the evidence cannot distinguish a delay in library import, model download, weight loading or inference. The local planner currently has no timeout or intermediate progress events. Repeated successful status-poll requests do not demonstrate progress of the review itself.

The root cause and fix remain unresolved. The next diagnostic step is to run the model import, load and one-action generation stages separately on the affected Windows machine, then add progress reporting and bounded model execution with tests. This report does not invalidate the recorded Linux results, but they do not establish Windows compatibility. The user's machine paths and private diagnostic log are not included in this public repository.
