"""Conditional edges.

classify's `content` is often meant to be a summarize step's output (see
worker_node._with_expert_context) — a real dependency, not an independent
task — so every summarize step must finish, and land in
state["step_results"], before any classify step starts. LangGraph only
merges a wave of parallel `Send`s into shared state once the whole wave
finishes, so this is two waves joined by a real edge, not one mixed wave:

  planner -> route_summarize_steps -> [expert]* -> classify_gate
                                                  -> route_classify_steps -> [worker]* -> aggregate

The planner (an LLM call) already decided which steps exist and what their
input is. Which wave runs first — and that summarize always finishes before
classify starts — is decided here, in plain code: deterministic, not a
model call. Still the same "map" (Send-per-step) / "reduce" (`operator.add`
on step_results) split as before, just split into two ordered waves.
"""

from __future__ import annotations

from langgraph.types import Send

from agents.graph.states import State


def route_summarize_steps(state: State) -> list[Send | str]:
    sends: list[Send | str] = [
        Send("expert", {"step": step})
        for step in state["plan"]
        if step["skill"] == "summarize"
    ]
    return sends if sends else ["classify_gate"]


def route_classify_steps(state: State) -> list[Send | str]:
    # Send() gives each worker call ONLY this dict as its state — none of
    # the outer graph state rides along automatically. worker_node reads
    # step_results (via _with_expert_context) to find a finished summarize
    # result, so it has to be included here explicitly, or every classify
    # step sees an empty step_results regardless of what already finished.
    step_results = state.get("step_results", [])
    sends: list[Send | str] = [
        Send("worker", {"step": step, "step_results": step_results})
        for step in state["plan"]
        if step["skill"] == "classify"
    ]
    return sends if sends else ["aggregate"]
