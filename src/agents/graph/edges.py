"""The graph's nodes and the one conditional edge. The orchestrator's model
picks every route; nodes/orchestrator/guardrails.py checks it before it
lands in `state["route"]`.
"""

from __future__ import annotations

from langgraph.graph import END

from agents.graph.states import State

# the agents a plan can use — one graph node each
AGENTS = ("validation", "compliance", "payroll-calculation", "execution")
# the ones that run in parallel before review; execution always runs last
STAGE_AGENTS = AGENTS[:-1]
NODES = ("planner", *AGENTS, "fetch", "review", END)


def route_from_orchestrator(state: State) -> list[str]:
    return state["route"]  # checked by guardrails.violations in the orchestrator node
