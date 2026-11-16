# Third-party notices and source references

The application code is MIT-licensed. Dependencies retain their licences; installing them through pip/npm preserves their own package licence files. Model weights and third-party source code are not redistributed in this ZIP. The complete installed Python versions are pinned in `requirements.txt`; npm resolution and integrity hashes are in `package-lock.json`.

| Dependency / reference | Role | Upstream |
| --- | --- | --- |
| LangGraph (MIT) | Open-source agent orchestration | https://github.com/langchain-ai/langgraph |
| MCP Python SDK (MIT) | Original server/client protocol implementation | https://github.com/modelcontextprotocol/python-sdk |
| Official filesystem MCP server (MIT) | Borrowed read-only rubric access | https://github.com/modelcontextprotocol/servers/tree/main/src/filesystem |
| Qwen2.5-0.5B-Instruct (Apache-2.0) | Default open-weights planner | https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct |
| Transformers (Apache-2.0), Hugging Face Hub (Apache-2.0) | Local inference and model cache | https://github.com/huggingface/transformers |
| PyTorch (BSD-style) | CPU tensor runtime | https://github.com/pytorch/pytorch |
| FastAPI (MIT), Starlette (BSD-3-Clause), Uvicorn (BSD-3-Clause) | HTTP application runtime | https://github.com/fastapi/fastapi |
| HTTPX (BSD-3-Clause), Pydantic (MIT) | HTTP adapter and request validation | https://github.com/encode/httpx |
| pytest (MIT), jsdom (MIT) | Automated verification | https://github.com/pytest-dev/pytest ; https://github.com/jsdom/jsdom |
| Pillow, ffmpeg, DejaVu fonts | Development-only recording renderer | https://python-pillow.github.io/ ; https://ffmpeg.org/ ; https://dejavu-fonts.github.io/ |

The default Qwen model revision is `7ae557604adf67be50417f59c2c2f167def9a775`. We did not train or fine-tune its weights. The recorded task uses its real logits with constrained JSON decoding.

API contracts reviewed on 12 November 2026:

- Google Gemini model and API documentation: https://ai.google.dev/gemini-api/docs/models and https://ai.google.dev/api/generate-content
- Moodle 4.2 implementation: https://github.com/moodle/moodle/blob/MOODLE_402_STABLE/grade/report/user/classes/external/user.php
- Moodle 4.5 implementation: https://github.com/moodle/moodle/blob/MOODLE_405_STABLE/grade/report/user/classes/external/user.php
- Moodle 4.5 API reference: https://phpdoc.moodledev.io/4.5/d7/da7/classgradereport__user_1_1external_1_1user.html
- Challenge requirements: https://agentic-africa-challenge.lovable.app/tracks/education

No Moodle PHP source is copied into this application. Moodle's licence applies to Moodle itself. Gemini is an optional hosted service subject to Google's terms and billing, not an open-weights dependency.
