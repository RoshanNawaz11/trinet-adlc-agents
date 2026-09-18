"""Create and validate an LLM-generated plan."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from agents.graph.states import State, Step
from agents.model.gateway import ModelGateway, get_default_gateway
from agents.skills.loader import list_skill_catalog
from json_utils import JSONParseError, extract_json
from prompting import render_prompt

logger = logging.getLogger(__name__)

_DIR = Path(__file__).parent
SYSTEM_PROMPT = (_DIR / "prompts" / "system.txt").read_text(encoding="utf-8")
PROMPT_PATH = _DIR / "prompts" / "prompt.jinja"


class PlanValidationError(ValueError):
    pass

def _validate_plan(parsed: object, valid_skill_names: set[str]) -> list[Step]:
    if not isinstance(parsed, dict):
        raise PlanValidationError("response must be a JSON object")
    raw_steps = parsed.get("plan")
    if not isinstance(raw_steps, list) or not raw_steps:
        raise PlanValidationError("'plan' must be a non-empty array")

    plan: list[Step] = []
    seen_ids: set[str] = set()
    for index, entry in enumerate(raw_steps, start=1):
        if not isinstance(entry, dict):
            raise PlanValidationError(f"step {index} must be an object")
        step_id = entry.get("step_id")
        skill = entry.get("skill")
        payload = entry.get("input")
        if not isinstance(step_id, str) or not step_id.strip():
            raise PlanValidationError(f"step {index} needs a non-empty step_id")
        if step_id in seen_ids:
            raise PlanValidationError(f"duplicate step_id {step_id!r}")
        if skill not in valid_skill_names:
            raise PlanValidationError(
                f"unknown skill {skill!r}; available: {sorted(valid_skill_names)}"
            )
        if not isinstance(payload, dict):
            raise PlanValidationError(f"step {step_id!r} input must be an object")
        if skill == "summarize" and not isinstance(payload.get("source_text"), str):
            raise PlanValidationError(f"step {step_id!r} summarize input needs source_text")
        if skill == "classify":
            if not isinstance(payload.get("content"), (str, dict)):
                raise PlanValidationError(f"step {step_id!r} classify input needs content")
            labels = payload.get("label_set")
            if labels is not None and (
                not isinstance(labels, list)
                or not labels
                or not all(isinstance(label, str) for label in labels)
            ):
                raise PlanValidationError(
                    f"step {step_id!r} label_set must be a non-empty string array"
                )
        seen_ids.add(step_id)
        plan.append(
            {
                "step_id": step_id,
                "skill": skill,
                "input": payload,
                "status": "pending",
                "attempt": 0,
            }
        )
    return plan


async def planner_node(state: State, gateway: ModelGateway | None = None) -> dict:
    query = state["query"]
    gateway = gateway or get_default_gateway()
    skills = list_skill_catalog()
    skill_names = {skill["name"] for skill in skills}
    logger.info("planner_node starting: query=%r available_skills=%s", query[:100], sorted(skill_names))
    if not skills:
        raise PlanValidationError("no skill bundles are available")

    retry_feedback: str | None = None
    last_error: Exception | None = None
    for attempt in range(1, 3):
        user_prompt = render_prompt(
            PROMPT_PATH,
            query=query,
            skills=skills,
            retry_feedback=retry_feedback,
        )
        raw = await gateway.complete("planner", system=SYSTEM_PROMPT, user=user_prompt)
        try:
            plan = _validate_plan(extract_json(raw), skill_names)
            logger.info(
                "planner_node done (attempt %d): %d step(s) — %s",
                attempt, len(plan), [(s["step_id"], s["skill"]) for s in plan],
            )
            return {"plan": plan}
        except (JSONParseError, PlanValidationError) as exc:
            last_error = exc
            retry_feedback = str(exc)
            logger.warning("planner_node attempt %d rejected: %s", attempt, exc)

    logger.error("planner_node failed after 2 attempts: %s", last_error)
    raise PlanValidationError(f"planner failed after two attempts: {last_error}")
