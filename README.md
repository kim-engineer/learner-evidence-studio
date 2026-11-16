# Learner Evidence Studio

An original teacher workspace for **longitudinal strength tracking**. It joins dated assessment records across terms, checks every finding against its sources, and stops at a draft that a named teacher must review.

Created for Werevu Academy with AI coding assistance. This is a new standalone application, with an optional Moodle importer. Extract it into its own folder. It is not a replacement-file overlay for the earlier Microsoft Moodle plugin migration. The earlier Gemini plugin and this application can be used separately.

## Start in one command

Install **Python 3.12** and **Node.js 22 or newer**, including npm. Clone this repository, or download and extract its ZIP:

```bash
git clone https://github.com/kim-engineer/learner-evidence-studio.git
cd learner-evidence-studio
```

From the project directory run:

```bash
python run.py
```

On Windows, if Python 3.12 is selected through the Python launcher, use `py -3.12 run.py`. The launcher creates `.venv`, installs the pinned dependencies and the borrowed MCP server, and starts the application. Linux x86_64 is the verified platform. The launcher includes Windows paths, but a completed review on Windows has not been verified. Allow at least 6 GB available memory and 5 GB disk space. Internet access is needed to install dependencies and download the approximately 1 GB model on the first local review.

Open **http://127.0.0.1:8088** and sign in:

| Field | Demo value |
| --- | --- |
| Username | `demo.teacher` |
| Password | `lesson-demo-2026` |
| Teacher | Amina Njeri (a fictional demo identity) |

Four synthetic learners are created automatically. Select Learner A and **Review evidence**. Follow the MCP calls under **Agent activity**, then inspect **Profile & review**. Each source chip opens its underlying record. Approve a checked draft with a review note. A separate conversation confirmation is required before a report can be downloaded. All demo confirmations concern fictional records.

The first model load takes longer. Subsequent runs reuse the model in memory. Closing the server leaves the database on disk. Run the same command to start again.

**Known Windows issue:** a user-reported local review remained running with zero completed model calls after the reference rubric was read. The current log cannot distinguish model import, download, loading or generation at that point, and local inference has no timeout or intermediate progress events. Repeated HTTP `200 OK` status requests only confirm that the status endpoint is responding. The cause is unresolved; see [EVALS.md](EVALS.md#windows-report--15-november-2026). Publishing this repository does not resolve that issue.

### Docker alternative

With Docker Desktop / Docker Engine and Compose installed:

```bash
docker compose up --build
```

The same local address and login apply. Compose uses a Linux amd64 CPU image and named volumes for the database and model cache. Stop with `docker compose down`. Do not add `-v` unless you intend to delete those volumes. The container recipe is included but was not executed in this build environment. The native launcher was tested from a fresh virtual environment.

## Use a Gemini API key

Copy `.env.example` to `.env`. Set `GEMINI_API_KEY` to your Google AI Studio key, then restart the server. Select **Gemini** in the workspace before starting a review. The default model ID is `gemini-3.5-flash-lite`; `GEMINI_MODEL` can select another available model that supports structured JSON output.

No Azure subscription, endpoint or Azure key is used anywhere in this application. Keys stay on the server. Gemini receives assessment percentages, skill tags and workflow state, so use cloud mode only when this processing is authorised. Learner names and free-text source notes are not sent to the planner. Gemini billing is separate from local mode. The Gemini request adapter was tested with mocked API responses; a live key was not supplied, so no live Gemini success is claimed.

For the challenge's open-weights requirement, keep at least one completed **Local open-weights model** run. The included evaluations and demo actually used Qwen2.5-0.5B-Instruct on CPU, with a pinned model revision. No key is needed for that mode.

## Bring your own records

Use **Add learner record** to create a separate pseudonymous history. Do not mix real records into the four synthetic learners. **Import evidence** accepts JSON matching [DATA_FORMAT.md](DATA_FORMAT.md). `data/import-example.json` is a complete synthetic example. Importing the same IDs and unchanged values again is safe. A changed value under an existing ID requires the explicit correction operation, which preserves an audit record and invalidates old drafts.

For Moodle, see [moodle/SETUP.md](moodle/SETUP.md). The connector uses `gradereport_user_get_grade_items`, with teacher-supplied mappings from activity grade items to skill tags and assessment dates. It has been checked against Moodle 4.2 and 4.5 API source and tested with representative HTTP fixtures. A live Moodle instance was not available for installation testing. This app does not modify Moodle's PHP files, theme or database schema.

## Verify or reproduce

After the launcher has installed dependencies, activate `.venv`:

```bash
# Linux/macOS shell (native pinned CPU environment is verified on Linux)
source .venv/bin/activate
# Windows PowerShell instead: .venv\Scripts\Activate.ps1
python -m pytest -q
python -m scripts.evaluate
```

For DOM integration checks, run `npm ci` to include the development-only jsdom dependency, then `python -m scripts.check_ui`. This exercises the actual HTTP application and a real local-model task. It is not a visual layout or browser accessibility audit.

`python -m scripts.demo` creates a new continuous timed terminal recording and full JSON trace in `evaluation/demo`. The supplied MP4 was rendered from such a real recording at its original speed. Rendering another MP4 requires Pillow and ffmpeg and uses `python -m scripts.render_recording`.

## What is included

| File or folder | Purpose |
| --- | --- |
| `studio/` | Application, interface, model adapter, LangGraph agent, custom MCP server |
| `reference/policy.json` | Reviewed demonstration rubric read through borrowed MCP |
| `data/` | Synthetic cohort and import example |
| `evaluation/final-runs/` | Six real open-weights traces, outcomes, token counts and timings |
| `evaluation/demo/` | Continuous terminal capture, MP4 and full run trace |
| [EVALS.md](EVALS.md) | Pass/fail tasks, run variation, unresolved limitation |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Agent shape and built/borrowed MCP boundaries |
| [DESCRIPTION.md](DESCRIPTION.md) | Submission description |
| [ORIGINALITY.md](ORIGINALITY.md) | Original implementation and dependency attribution |
| [CODE_WALKTHROUGH.md](CODE_WALKTHROUGH.md) | How to explain and extend the project |
| [SUBMISSION_STATUS.md](SUBMISSION_STATUS.md) | Completed work and remaining submission steps |

This is a local demonstration and evaluation build. It has one configured teacher account, application-level audit records, and no production identity provisioning, encrypted database or verified school deployment. The rubric is illustrative, not a validated measure of aptitude. A school pilot needs an actual teacher's review, suitable consent, access controls and assessment-comparability work. No learner ranking, diagnosis or automatic subject/career assignment is produced.

## Account configuration

`STUDIO_TEACHER_NAME` and `STUDIO_PASSWORD` in `.env` set the first account when a new database is created. Changing these variables does not silently alter an existing account. `python -m scripts.change_account` updates the existing demo teacher's display name/password interactively and signs out existing sessions. Keep the default network binding on localhost for this prototype.

Licence: [MIT](LICENSE). Dependency and model licences remain their own; see [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
