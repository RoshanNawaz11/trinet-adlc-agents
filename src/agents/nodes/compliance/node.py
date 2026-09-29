"""Compliance Agent — Stage 2. Its rules live in skills/compliance/skill.md."""

from __future__ import annotations

from agents.graph.states import State
from agents.model.gateway import ModelGateway
from agents.nodes.stage_agent import run_stage_agent


async def compliance_node(state: State, gateway: ModelGateway | None = None) -> dict:
    return await run_stage_agent("compliance", "compliance", "Compliance Agent", state, gateway=gateway)
