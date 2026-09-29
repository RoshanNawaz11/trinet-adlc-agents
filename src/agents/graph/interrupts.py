"""Human review before execution.

The run does all its analysis first, then stops here only if it raised
flags. Each pause is one `interrupt()` for the earliest unresolved flag; the
reviewer's Decision comes back as the resume value. Confirm resolves the
flag, decline keeps it open with the reason recorded. Control then returns
to the orchestrator, which sends the run back here while any flag is still
open and on to execution once none is.
"""

from __future__ import annotations

from langgraph.types import interrupt

from agents.graph.states import Decision, Flag, State, step_record


def pending_flag(state: State) -> Flag | None:
    return next((f for f in state.get("flags", []) if not f["resolved"]), None)


def review_node(state: State) -> dict:
    flag = pending_flag(state)
    if flag is None:
        return {}

    decision: Decision = interrupt({"flag": flag})

    action = decision["action"]
    updated: Flag = {
        **flag,
        "resolved": action == "confirm",
        "decisions": [*flag["decisions"], decision],
    }
    title = f"{flag['title']}: {'confirmed' if action == 'confirm' else 'declined'} by reviewer"
    evidence = {k: v for k, v in decision.items() if k in ("value", "reason")}
    return {
        "flags": [updated],
        "steps": [step_record(flag["stage"], "Reviewer", title, "Console", result=action, evidence=evidence)],
    }
