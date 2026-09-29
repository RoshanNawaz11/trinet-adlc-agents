"""Orchestrator — the hub. No model call: the planner decides what to run, and
the orchestrator runs that plan.

Control comes here at the start and after the planner, every agent and every
review. Each visit it refreshes the fields the UI shows — status, flagged,
confidence, priority — from what has been reported so far.

Where the run goes next is decided by graph.edges.route_from_orchestrator.
"""

from __future__ import annotations

from typing import Any

from agents.graph.edges import AGENTS, next_step
from agents.graph.interrupts import pending_flag
from agents.graph.states import State

_RAISED = {"low": "medium", "medium": "high", "high": "high"}


def orchestrator_node(state: State) -> dict[str, Any]:
    results = state.get("results") or {}
    if "planner" not in results:
        return {"status": "running"}  # first visit: off to the planner

    flagged = pending_flag(state) is not None
    update: dict[str, Any] = {
        "flagged": flagged,
        # An unresolved flag outranks a finished plan, so an order the planner
        # declined to run still comes back as needing review.
        "status": "needs_review" if flagged else "done" if next_step(state) is None else "running",
    }
    base = results.get("planner", {}).get("priority")
    if base:
        # raised one level once any agent has flagged the order, and kept raised
        update["priority"] = _RAISED[base] if state.get("flags") else base
    scores = [results[a]["confidence"] for a in AGENTS if "confidence" in results.get(a, {})]
    if scores:
        update["confidence"] = round(min(scores) * 100)
    return update
