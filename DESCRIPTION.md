# Submission description

Learner Evidence Studio helps a teacher notice patterns that disappear when assessment records are viewed one term at a time. It fits the longitudinal strength tracking theme. The prototype serves the end-of-term review workflow of Demo Primary School, a fictional Kenyan public-school setting. Amina Njeri is its explicitly fictional teacher account. No school partnership or teacher interview is claimed.

A teacher opens one learner's history, reviews dated quizzes and assignments, and requests an evidence review. An agent decides which history to retrieve and which analytical view to examine. It reads a school rubric through an existing MCP server, uses our own MCP tools to calculate patterns, checks those findings against their sources, and saves a draft. When the initial analytical view misses substantial change, the validator sends the agent back for another check. Every claimed pattern links to exact source records.

The interface keeps uncertain handwriting, late entries and missing history visible. Uncertain scores do not enter calculations, and two terms cannot establish a sustained pattern. A teacher must approve the specific draft and record a guardian conversation before a reviewed report becomes downloadable. The application never ranks classmates or assigns a subject or career track.

The default planner is a small downloadable Qwen model running on CPU, orchestrated with LangGraph. Gemini is optional. Moodle grades can be imported through its existing web-service API after a teacher maps activity items to skills and dates. Names and free-text notes do not enter the model prompt.

The package includes reproducible synthetic data, actual local-model traces, repeat-run comparisons, an evaluation suite and a continuous terminal demonstration. Its current limitation is assessment comparability: changed quiz difficulty can resemble learner progress. The next step is a consented teacher-led pilot using reviewed assessment rubrics, with evidence about usability and time saved before making effectiveness claims.
