# Submission status

This repository contains the original application source and evidence of local Linux execution. The public source is at [kim-engineer/learner-evidence-studio](https://github.com/kim-engineer/learner-evidence-studio). It has not been submitted to the challenge. The checklist maps the [education brief](https://agentic-africa-challenge.lovable.app/tracks/education) to the deliverables without claiming organiser acceptance.

| Requirement | What is delivered | Remaining action |
| --- | --- | --- |
| One education theme | Longitudinal strength tracking | Keep this as the single submitted theme |
| Own MCP server, at least three tools, including an action | Four tools; `save_profile_draft` persists a validated draft | Demonstrate these boundaries in your review |
| A borrowed MCP server | Official read-only filesystem server, pinned package | Explain its rubric-access role |
| Open-source orchestration | LangGraph plan/act graph with feedback and bounded retries | Understand and be ready to modify it live |
| Full open-weights task | Six real recorded Linux evaluations plus a recorded terminal demo | Resolve the reported Windows review stall and verify a completed run on that machine |
| Logs and named approval gates | Timestamped tool inputs/outputs, authenticated hash-bound approval, conversation gate | Configure your real teacher identity before a pilot |
| Original work with attribution | New application, MIT licence, originality statement and dependency notices | Retain AI-assistance and dependency disclosures |
| Public OSI-licensed repository with one-command setup | Public source repository; native `python run.py` verified on Linux; MIT licence | Test a fresh clone on the intended deployment machine |
| Public video under three minutes | `evaluation/demo/agent-demo.mp4`, approximately 26 seconds; continuous real terminal run | Upload to YouTube or Vimeo and verify public access |
| Around 300-word description | `DESCRIPTION.md` | Add truthful school/teacher research if you conduct it |
| One-page architecture | `ARCHITECTURE.md` | Review before submission |
| At least eight evaluated tasks, including unresolved failure | `EVALS.md`, actual traces, pass/fail results and repeat-run variation | Keep failed and untested items visible |

## About the included recording

The MP4 renders the actual timestamped terminal capture in `agent-run.cast` at its original speed, with no cuts or acceleration. It shows real model decisions, MCP calls, a failed validation, recovery, draft persistence and the pause for teacher review. Full payloads accompany it in `agent-run.json`; the terminal shows readable summaries of large payloads. It has no narration and is not a browser recording. For a stronger presentation, record your own short continuous run in the teacher interface, with Agent activity visible and your explanation of the failure and gate. Do not portray the fictional teacher as someone interviewed.

## Before claiming classroom readiness

No actual school partnership, teacher interview or measured time saving has been established. The demo school and teacher are fictional. The demonstration rubric needs review with a real teacher, and assessment comparability remains unresolved. Live Moodle and Gemini connection checks also remain outstanding because credentials were not provided. These facts affect classroom-fit and reliability claims even when the code and submission materials are complete.

The reported Windows review-loading issue also remains unresolved. See [EVALS.md](EVALS.md#windows-report--15-november-2026) for the observed symptoms and diagnostic limits. The repository upload is a source publication, not evidence of a working Windows review or completed challenge submission.

Use the supplied code walkthrough to prepare for the technical review. The documentation and tests give you a starting point for taking ownership through understanding, adaptation and real classroom feedback.
