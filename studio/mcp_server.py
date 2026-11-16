"""The original MCP server. Agent sessions are scoped to a persisted learner/run."""
import functools
import os

from mcp.server.fastmcp import FastMCP

from . import evidence
from .store import audit, db

server = FastMCP("Learner Evidence Studio")
RUN_ID = os.environ.get("STUDIO_RUN_ID", "")


def scoped_tool(function):
    name = {"_get": "get_learner_evidence", "_assess": "assess_longitudinal_patterns",
            "_validate": "validate_learner_profile", "_save": "save_profile_draft"}[function.__name__]
    @functools.wraps(function)
    def wrapped(**arguments):
        try:
            with db(True) as connection:
                run = connection.execute("SELECT * FROM runs WHERE id=?", (RUN_ID,)).fetchone()
                if run is None or run["status"] != "running":
                    raise ValueError("An active, application-issued run is required")
                if arguments["learner_id"] != run["learner_id"]:
                    raise ValueError("Tool access is restricted to this run's learner")
                result = function(connection=connection, run_id=RUN_ID, **arguments)
                audit(connection, "agent", name, arguments, result, RUN_ID)
                return result
        except Exception as exc:
            with db(True) as connection:
                audit(connection, "agent", name, arguments, {"error": str(exc)}, RUN_ID, "error")
            raise
    return wrapped


# Public signatures stay explicit for the MCP tool schemas.
@server.tool()
def get_learner_evidence(learner_id: str, scope: str = "recent") -> dict:
    """Read dated source assessments and context for the run's learner. Scope is recent or all."""
    return _get(learner_id=learner_id, scope=scope)


@scoped_tool
def _get(*, connection, run_id, learner_id, scope):
    return evidence.get_evidence(connection, learner_id, scope)


@server.tool()
def assess_longitudinal_patterns(learner_id: str, scope: str, lens: str, policy: dict) -> dict:
    """Compute cited patterns. Use trajectory or consistency and the rubric read from the reference MCP server."""
    return _assess(learner_id=learner_id, scope=scope, lens=lens, policy=policy)


@scoped_tool
def _assess(*, connection, run_id, learner_id, scope, lens, policy):
    return evidence.assess(connection, learner_id, scope, lens, policy)


@server.tool()
def validate_learner_profile(learner_id: str, draft: dict) -> dict:
    """Recompute every finding from its evidence, detect altered claims, and check complete history."""
    return _validate(learner_id=learner_id, draft=draft)


@scoped_tool
def _validate(*, connection, run_id, learner_id, draft):
    return evidence.validate(connection, learner_id, draft)


@server.tool()
def save_profile_draft(learner_id: str, draft: dict) -> dict:
    """Persist a validated, cited draft for teacher review. This operation never approves or releases it."""
    return _save(learner_id=learner_id, draft=draft)


@scoped_tool
def _save(*, connection, run_id, learner_id, draft):
    return evidence.save_draft(connection, learner_id, run_id, draft)


if __name__ == "__main__":
    server.run(transport="stdio")
