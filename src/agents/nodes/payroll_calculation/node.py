"""Payroll Calculation Agent — Stage 3. Its rules live in skills/payroll-calculation/skill.md."""

from __future__ import annotations

from agents.graph.states import State
from agents.model.gateway import ModelGateway
from agents.nodes.stage_agent import run_stage_agent


async def payroll_calculation_node(state: State, gateway: ModelGateway | None = None) -> dict:
    return await run_stage_agent(
        "payroll-calculation", 
        "payroll", 
        "Payroll Calculation Agent", 
        state, 
        gateway=gateway
    )
