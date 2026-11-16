# Original work and attribution

This standalone implementation was created for Werevu Academy in this working session, with ChatGPT/Codex providing AI coding assistance under the user's direction. Its application code, teacher interface, data schema, synthetic cohort, review process, evaluation scripts and documentation were written for this project.

The earlier request involved adapting Microsoft's `microsoft/moodle-ai-assistant` to Gemini. That existing PHP plugin is not the foundation of this rebuild and its implementation is not bundled here. The new application communicates with Moodle's standard REST interface through a new Python connector. It can be developed and demonstrated independently of the earlier migration.

The project-specific contribution is the combination of dated, individually cited evidence; a local model selecting bounded review actions; validation that catches an incomplete analytical view; and approval bound to an exact draft and evidence revision. The interface brings those decisions and their sources into one teacher workspace. These are implementation and design contributions, not a claim that the general idea of learner profiling has never existed.

The education theme and challenge requirements come from the [Agentic AI for Africa education brief](https://agentic-africa-challenge.lovable.app/tracks/education). LangGraph, the MCP SDK, the official filesystem MCP server, Transformers, Qwen and other dependencies are credited in `THIRD_PARTY_NOTICES.md`. Their implementation and model weights are not represented as our own work.

The original application files are offered under MIT, with Werevu Academy as the project copyright attribution. Open-source licensing permits other people to use and adapt the work under the licence. It does not make the third-party dependencies exclusive to this project. No legal guarantee of exclusive ownership, patentability or global novelty is asserted.

For a truthful presentation, explain that you directed an AI-assisted build and can walk through, test and adapt its code. Use `CODE_WALKTHROUGH.md` to prepare. Keep dependency attribution, disclose the synthetic school and learner data, and replace assumptions with findings from your own teacher discussions as the project develops.
