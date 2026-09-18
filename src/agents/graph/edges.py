"""Conditional edges.

`route_after_planner` is what turns a `Plan` (an ordered list of steps) into
parallel work: for each step, it emits a `Send(target_node, partial_state)`.
LangGraph runs every emitted `Send` as its own node invocation, in parallel,
each with only the state that `Send` gave it (here, just `{"step": ...}`) —
this is the "map" half of a map-reduce; `state.py`'s `operator.add` reducer
on `step_results` is the "reduce" half.
"""

from __future__ import annotations

from langgraph.types import Send

from agents.graph.states import State

NODE_FOR_SKILL = {
    "summarize": "expert",
    "classify": "worker",
}


def route_after_planner(state: State) -> list[Send]:
    sends: list[Send] = []
    for step in state["plan"]:
        target = NODE_FOR_SKILL.get(step["skill"])
        if target is None:
            raise ValueError(f"No node registered for skill: {step['skill']}")
        sends.append(Send(target, {"step": step}))
    return sends
