"""Planner — builds the plan the orchestrator runs. Its rules live in
skills/planner/skill.md.

It plans again, once, when the output validator finds issues in execution's
package: the new plan holds only the agents to run again.
"""

from __future__ import annotations

import json
import logging
from datetime import date
from typing import Any

from agents.graph.edges import AGENTS, OUTPUT_VALIDATOR
from agents.graph.states import PlanStep, State, step_record
from agents.model.gateway import ModelGateway, get_default_gateway
from agents.skills.client import run_skill
from agents.skills.registry import ensure_bundle_published
from json_utils import extract_json

logger = logging.getLogger(__name__)

_BUNDLE = "planner"
_JSON_INSTRUCTION = (
    "Your final answer must be a single JSON object: "
    '{"work": ["<kind of work>", ...], '
    '"priority": "high" | "medium" | "low", '
    '"plan": [{"agent": "<agent name>", "task": "<one sentence>"}], or an empty list when the order asks for nothing, '
    '"reason": "<one short sentence>"}. '
    "Return ONLY JSON — no preamble, no markdown fences."
)
_PRIORITIES = ("high", "medium", "low")
# the first plan, plus one re-plan after the output validator finds issues
MAX_PLANS = 2


class PlannerOutputError(ValueError):
    pass


def _check(parsed: Any, replan: bool) -> tuple[list[PlanStep], str, str]:
    if not isinstance(parsed, dict):
        raise PlannerOutputError("planner: answer must be a JSON object")
    plan, priority = parsed.get("plan"), parsed.get("priority")
    if not isinstance(plan, list) or not all(isinstance(s, dict) for s in plan):
        raise PlannerOutputError("planner: 'plan' must be a list of steps")
    # an empty plan ends the run without review — a re-plan must run something
    if replan and not plan:
        raise PlannerOutputError("planner: a re-plan must re-run at least execution")
    # An empty plan is a decision: this order is not a termination, so none of
    # the termination agents should run. A non-empty plan still has to be a
    # real route through those agents.
    if plan:
        agents = [s.get("agent") for s in plan]
        if unknown := [a for a in agents if a not in AGENTS]:
            raise PlannerOutputError(f"planner: unknown agents {unknown}; use {list(AGENTS)}")
        if len(set(agents)) != len(agents):
            raise PlannerOutputError(f"planner: an agent appears twice in {agents}")
        if agents[-1] != "execution":
            raise PlannerOutputError(f"planner: execution must be the last step, got {agents}")
    if priority not in _PRIORITIES:
        raise PlannerOutputError(f"planner: priority must be high|medium|low, got {priority!r}")
    steps: list[PlanStep] = [{"agent": s["agent"], "task": str(s.get("task") or "")} for s in plan]
    return steps, priority, str(parsed.get("reason") or "")


async def planner_node(state: State, gateway: ModelGateway | None = None) -> dict[str, Any]:
    gateway = gateway or get_default_gateway()
    skill_id, version_id = await ensure_bundle_published(_BUNDLE, gateway=gateway)
    config = gateway.policy.get(_BUNDLE, gateway.policy["default"])
    plans = (state.get("runs") or {}).get(_BUNDLE, 0) + 1
    replan = plans > 1
    # the model doesn't know the date; priority compares deadlines with it
    brief: dict[str, Any] = {
        "today": date.today().isoformat(),
        "service_order": state.get("service_order") or state.get("query"),
    }
    if replan:
        # what ran last time, and what the output validator found wrong with it
        brief["previous_plan"] = (state.get("results") or {}).get(_BUNDLE)
        brief[OUTPUT_VALIDATOR] = (state.get("results") or {}).get(OUTPUT_VALIDATOR)
    executed = await run_skill(
        skill_id, version_id,
        json.dumps(brief, default=str, ensure_ascii=False),
        model=config["model"], additional_instructions=_JSON_INSTRUCTION, gateway=gateway,
    )
    parsed = extract_json(executed["raw_response"], key="plan")
    plan, priority, reason = _check(parsed, replan)
    # the kinds of work the order asks for, so agents don't decide them again
    work = [str(w) for w in parsed.get("work") or [] if w]
    logger.info("planner: plan=%s priority=%s replan=%s", [s["agent"] for s in plan], priority, replan)

    update: dict[str, Any] = {
        "plan": plan,
        "priority": priority,
        "results": {_BUNDLE: {"work": work, "plan": plan, "priority": priority, "reason": reason}},
        "runs": {_BUNDLE: plans},
        "steps": [step_record(
            "planning",
            "Planner",
            f"Re-planned {len(plan)} steps" if replan else f"Planned {len(plan)} steps" if plan else "Nothing to run",
            "Agents",
            result=" → ".join(s["agent"] for s in plan) if plan else "No agents scheduled",
            evidence={"priority": priority, "reason": reason},
            feed="handoff",
        )],
    }
    if replan:
        # the agents run again — seeing their previous result and worker results,
        # so they fix only what their task names — and the validator checks again
        again = [s["agent"] for s in plan]
        results = state.get("results") or {}
        update["results"] |= {a: {**(results.get(a) or {}), "rerun": True} for a in (*again, OUTPUT_VALIDATOR)}
        update["runs"] |= {a: 0 for a in again}
    if not plan:
        update["flagged"] = True
        update["flags"] = [{
            "flag_id": "planner-1",
            "type": "outOfScope",
            "stage": "planning",
            "title": reason or "Nothing to run for this order",
            "detail": {
                "reason": reason or "The order asks for nothing the agents can do.",
                "impact": "No agents were scheduled for this order.",
            },
            "resolved": False,
            "decisions": [],
        }]
    return update
