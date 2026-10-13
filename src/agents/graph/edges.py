"""The graph's nodes and the one conditional edge. The orchestrator's model
picks every route; nodes/orchestrator/route_rules.py checks it before it
lands in `state["route"]`.
"""

from __future__ import annotations

from langgraph.graph import END

from agents.graph.states import State

# the agents a plan can use — one graph node each
AGENTS = ("validation", "compliance", "payroll-calculation", "execution")
# the ones that run before execution; execution always runs last
STAGE_AGENTS = AGENTS[:-1]
# checks execution's package before review; not in the plan — it always follows execution
OUTPUT_VALIDATOR = "output-validator"
NODES = ("planner", *AGENTS, OUTPUT_VALIDATOR, "fetch", "review", END)


def route_from_orchestrator(state: State) -> list[str]:
    return state["route"]  # checked by route_rules.broken_rules in the orchestrator node
