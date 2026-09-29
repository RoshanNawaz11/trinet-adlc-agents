"""Where the run goes each time control returns to the orchestrator.

Hub and spoke: the planner and every agent report back to the orchestrator,
and this decides the next hop from the state alone — no model call, so a
run's path is predictable and auditable.

    no plan yet                       → planner
    next plan step is execution
      and a flag is still unresolved  → review
    next unfinished plan step         → that agent
    every step done                   → END
"""

from __future__ import annotations

from langgraph.graph import END

from agents.graph.interrupts import pending_flag
from agents.graph.states import State

# the agents a plan can use — one graph node each
AGENTS = ("validation", "compliance", "payroll-calculation", "execution")


def next_step(state: State) -> str | None:
    """The agent of the first plan step that has not reported yet."""
    results = state.get("results") or {}
    for step in state.get("plan") or []:
        if step["agent"] not in results:
            return step["agent"]
    return None


def route_from_orchestrator(state: State) -> str:
    if not state.get("plan"):
        return "planner"
    agent = next_step(state)
    if agent is None:
        return END
    if agent == "execution" and pending_flag(state):
        return "review"
    return agent
