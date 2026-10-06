"""Execution Agent — Stage 4. Its rules live in skills/execution/skill.md.

Prepare only: it builds the package a person acts on afterwards — the final
payment for a termination, the setup package for an onboarding. It runs after
every other agent and before the final review, and raises no flags.
"""

from __future__ import annotations

from agents.graph.states import State
from agents.model.gateway import ModelGateway
from agents.nodes.stage_agent import run_stage_agent

_JSON_INSTRUCTION = (
    "Your final answer must be a single JSON object: "
    '{"steps": [{"title": "<what was done and the outcome>", "source": "<system or input used>", '
    '"result": "<short result>", "evidence": {<key facts>}}], '
    '"output": {<the package(s) and status described in your skill>}, '
    '"confidence": <0.0-1.0, how sure you are the package is right>}. '
    "Return ONLY JSON — no preamble, no markdown fences."
)


async def execution_node(state: State, gateway: ModelGateway | None = None) -> dict:
    update = await run_stage_agent(
        "execution", "execution", "Execution Agent", state,
        gateway=gateway, json_instruction=_JSON_INSTRUCTION, with_tools=True,
    )
    return {**update, "final_output": update["results"]["execution"]}
