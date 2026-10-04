"""Human review before execution: one approval of the whole run, after every
agent has finished. The reviewer sees each agent's result and every flag, and
approves (execution runs) or rejects (the run ends).
"""

from __future__ import annotations

from langgraph.types import interrupt

from agents.graph.states import Flag, Review, State, step_record


def open_flags(state: State) -> list[Flag]:
    """The flags still standing — merged duplicates are left out."""
    return [f for f in state.get("flags", []) if not f["resolved"]]


def review_node(state: State) -> dict:
    results = state.get("results") or {}
    flags = open_flags(state)
    decision: Review = interrupt({
        "service_order_id": state.get("service_order_id"),
        "summary": state.get("summary"),
        "results": {a: r for a, r in results.items() if a != "planner"},
        "flags": flags,
    })

    action = decision["action"]
    review: Review = {"action": action, "flags_seen": [f["flag_id"] for f in flags]}
    if decision.get("reason"):
        review["reason"] = decision["reason"]
    return {
        "review": review,
        "steps": [step_record(
            "planning", "Reviewer", f"Run {'approved' if action == 'approve' else 'rejected'} by reviewer",
            "Console", result=action, evidence={"reason": review["reason"]} if "reason" in review else {},
        )],
    }
