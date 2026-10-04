"""What a route must never do. The orchestrator's model picks every route
(skills/orchestrator/skill.md); `violations` is checked before a route is
accepted — it rejects, it never chooses.
"""

from __future__ import annotations

from langgraph.graph import END

from agents.graph.edges import NODES, STAGE_AGENTS
from agents.graph.states import State
from agents.nodes.stage_agent import MAX_RUNS

# nodes that never run alongside another
_ALONE = ("planner", "review", "execution", END)


def violations(state: State, route: list[str]) -> list[str]:
    """Why `route` can't run now — empty when it can."""
    if not route:
        return ["route is empty"]
    if unknown := [n for n in route if n not in NODES]:
        return [f"unknown nodes {unknown}; use {list(NODES)}"]
    if len(route) > 1 and (alone := [n for n in route if n in _ALONE]):
        return [f"{alone} must run alone"]

    results = state.get("results") or {}
    planned = {s["agent"] for s in state.get("plan") or []}
    open_needs = [n for n in state.get("needs") or [] if n["status"] == "open"]
    runs = state.get("runs") or {}
    review = (state.get("review") or {}).get("action")
    unfinished = [a for a in STAGE_AGENTS if a in planned and a not in results]
    errors: list[str] = []

    if "planner" not in results and route != ["planner"]:
        errors.append("the planner has not run yet — route to planner first")
    if "planner" in route and "planner" in results:
        errors.append("the planner already ran")
    if review and any(n in route for n in (*STAGE_AGENTS, "fetch", "review")):
        errors.append(f"the run was already reviewed ({review}) — only execution or __end__ can follow")
    for agent in STAGE_AGENTS:
        if agent not in route:
            continue
        if agent not in planned and not any(n["ask"] == agent for n in open_needs):
            errors.append(f"{agent} is not in the plan and nobody asked it anything")
        if waiting := [n["id"] for n in open_needs if n["from_agent"] == agent]:
            errors.append(f"{agent} is waiting on {waiting} — answer or fail those first")
        if runs.get(agent, 0) >= MAX_RUNS:
            errors.append(f"{agent} already ran {MAX_RUNS} times — fail what it was asked instead")
    if "fetch" in route and not any(n["ask"] == "execution" for n in open_needs):
        errors.append("fetch needs an open request to execution")
    if "review" in route:
        if not planned:
            errors.append("an empty plan has nothing to review — route __end__")
        if unfinished:
            errors.append(f"review comes once every agent has finished; still running: {unfinished}")
        if open_needs:
            errors.append(f"review must wait until every request is answered or failed: {[n['id'] for n in open_needs]}")
    if "execution" in route:
        if "execution" not in planned:
            errors.append("execution is not in the plan")
        if review != "approve":
            errors.append("execution runs only after the reviewer approves the run")
        if "execution" in results:
            errors.append("execution already ran")
    if route == [END] and planned:
        if not review:
            errors.append("the run can't end before review — finish the agents, then route review")
        elif review == "approve" and "execution" in planned and "execution" not in results:
            errors.append("the reviewer approved — route execution")
    return errors
