"""Shared runner for the stage agents (validation, compliance, payroll
calculation, execution). Same shape as the orchestrator:
"""

from __future__ import annotations

import json
import logging
from typing import Any

from agents.graph.states import Flag, Stage, State, step_record
from agents.model.gateway import ModelGateway, get_default_gateway
from agents.skills.registry import ensure_bundle_published
from agents.tools.bindings import complete_with_mcp_tools
from json_utils import extract_json

logger = logging.getLogger(__name__)

JSON_INSTRUCTION = (
    "Your final answer must be a single JSON object: "
    '{"steps": [{"title": "<what was checked and the outcome>", "source": "<system or tool used>", '
    '"result": "<short result>", "evidence": {<key facts>}}], '
    '"flags": [{"type": "<flag type from your skill>", "title": "<short title>", "detail": {<facts a reviewer needs>}}], '
    '"output": {<your findings for the agents after you>}, '
    '"confidence": <0.0-1.0, how sure you are of your findings>}. '
    "Use an empty flags list when nothing needs a human. "
    "Return ONLY JSON — no preamble, no markdown fences."
)


class AgentOutputError(ValueError):
    pass


def _input(state: State, bundle: str) -> str:
    return json.dumps(
        {
            # this agent's step in the planner's plan
            "task": next((s["task"] for s in state.get("plan") or [] if s["agent"] == bundle), ""),
            "service_order": state.get("service_order") or state.get("query"),
            "lookups": state.get("mcp_results") or [],
            "previous_results": state.get("results") or {},
            "flags": state.get("flags") or [],
        },
        indent=2,
        default=str,
        ensure_ascii=False,
    )


def _parse(raw: str, bundle: str) -> dict[str, Any]:
    parsed = extract_json(raw)
    if not isinstance(parsed, dict):
        raise AgentOutputError(f"{bundle}: answer must be a JSON object")
    steps, flags, output = parsed.get("steps"), parsed.get("flags", []), parsed.get("output")
    if not isinstance(steps, list) or not all(isinstance(s, dict) and s.get("title") for s in steps):
        raise AgentOutputError(f"{bundle}: 'steps' must be a list of objects with a title")
    if not isinstance(flags, list) or not all(isinstance(f, dict) and f.get("type") for f in flags):
        raise AgentOutputError(f"{bundle}: 'flags' must be a list of objects with a type")
    if not isinstance(output, dict):
        raise AgentOutputError(f"{bundle}: 'output' must be an object")
    confidence = parsed.get("confidence")
    if isinstance(confidence, bool) or not isinstance(confidence, int | float) or not 0 <= confidence <= 1:
        raise AgentOutputError(f"{bundle}: 'confidence' must be a number from 0 to 1")
    return parsed


async def run_stage_agent(
    bundle: str,
    stage: Stage,
    agent: str,
    state: State,
    *,
    gateway: ModelGateway | None = None,
    json_instruction: str = JSON_INSTRUCTION,
) -> dict[str, Any]:

    """Run one stage agent and return its state update: results, steps, flags."""
    gateway = gateway or get_default_gateway()
    logger.info("[%s] starting", bundle)

    skill = await ensure_bundle_published(bundle, gateway=gateway)
    raw, mcp_calls = await complete_with_mcp_tools(
        bundle, 
        system=json_instruction, 
        user=_input(state, bundle),
        gateway=gateway, 
        skill=skill
    )
    parsed = _parse(raw, bundle)

    # what agents did for the entire timeline (mcp calls and their own steps)
    steps = [
        step_record(
            stage, 
            agent, f"Looked up {call['tool']}", 
            f"MCP · {call['tool']}",
            result="error" if call.get("error") else "ok",
            evidence=call["input"],
            at=call["at"],
        )
        for call in mcp_calls
    ]
    # what this agent did for the entire timeline (their own steps)
    steps += [
        step_record(
            stage, 
            agent, 
            str(s["title"]), 
            str(s.get("source") or "Agents"),
            result=str(s.get("result") or ""), 
            evidence=s.get("evidence") or {},
        )
        for s in parsed["steps"]
    ]

    # when to route to manual review
    flags: list[Flag] = [
        {
            "flag_id": f"{bundle}-{i}",
            "type": str(f["type"]),
            "stage": stage,
            "title": str(f.get("title") or f["type"]),
            "detail": f.get("detail") or {},
            "resolved": False,
            "decisions": [],
        }
        for i, f in enumerate(parsed.get("flags", []), start=1)
    ]
    logger.info("[%s] done: steps=%d flags=%d mcp_calls=%d", bundle, len(steps), len(flags), len(mcp_calls))
    return {
        "results": {bundle: {**parsed["output"], "confidence": parsed["confidence"]}},
        "steps": steps,
        "flags": flags,
      }
