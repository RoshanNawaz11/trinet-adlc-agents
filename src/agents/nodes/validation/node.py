"""Validation Agent — Stage 1. Its rules live in skills/validation/skill.md."""

from __future__ import annotations

from agents.graph.states import State
from agents.model.gateway import ModelGateway
from agents.nodes.stage_agent import run_stage_agent


async def validation_node(state: State, gateway: ModelGateway | None = None) -> dict:
    # no tools: like the other agents, it asks execution for records (fetch answers)
    return await run_stage_agent(
        "validation", 
        "validation", 
        "Validation Agent", 
        state, 
        gateway=gateway,
    )
