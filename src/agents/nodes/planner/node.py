"""Planner — builds the plan the orchestrator runs. Its rules live in
skills/planner/skill.md.

One model call with the skill, no MCP tools: the order is already fetched,
and only the Execution agent talks to outside systems. The plan is checked in
code before the orchestrator runs it.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from agents.graph.edges import AGENTS
from agents.graph.states import PlanStep, State, step_record
from agents.model.gateway import ModelGateway, get_default_gateway
from agents.skills.client import run_skill
from agents.skills.registry import ensure_bundle_published
from json_utils import extract_json

logger = logging.getLogger(__name__)

_BUNDLE = "planner"
_JSON_INSTRUCTION = (
    "Your final answer must be a single JSON object: "
    '{"priority": "high" | "medium" | "low", '
    '"plan": [{"agent": "<agent name>", "task": "<one sentence>"}], '
    '"reason": "<one short sentence>"}. '
    "Return ONLY JSON — no preamble, no markdown fences."
)
_PRIORITIES = ("high", "medium", "low")


class PlannerOutputError(ValueError):
    pass


def _check(parsed: Any) -> tuple[list[PlanStep], str, str]:
    if not isinstance(parsed, dict):
        raise PlannerOutputError("planner: answer must be a JSON object")
    plan, priority = parsed.get("plan"), parsed.get("priority")
    if not isinstance(plan, list) or not plan or not all(isinstance(s, dict) for s in plan):
        raise PlannerOutputError("planner: 'plan' must be a non-empty list of steps")
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
    executed = await run_skill(
        skill_id, version_id,
        json.dumps({"service_order": state.get("service_order") or state.get("query")},
                   default=str, ensure_ascii=False),
        model=config["model"], additional_instructions=_JSON_INSTRUCTION, gateway=gateway,
    )
    plan, priority, reason = _check(extract_json(executed["raw_response"]))
    logger.info("planner: plan=%s priority=%s", [s["agent"] for s in plan], priority)

    return {
        "plan": plan,
        "priority": priority,
        "results": {_BUNDLE: {"plan": plan, "priority": priority, "reason": reason}},
        "steps": [step_record(
            "planning", "Planner", f"Planned {len(plan)} steps", "Agents",
            result=" → ".join(s["agent"] for s in plan),
            evidence={"priority": priority, "reason": reason},
        )],
    }
