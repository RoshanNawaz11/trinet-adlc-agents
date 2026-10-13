"""Output Validator — checks Execution's package against the results it was
built from. Runs after execution and before review; when it finds issues the
orchestrator sends the run back to the planner. Its rules live in
skills/output-validator/skill.md.
"""

from __future__ import annotations

from agents.graph.states import State
from agents.model.gateway import ModelGateway
from agents.nodes.stage_agent import run_stage_agent

_JSON_INSTRUCTION = (
    "Your final answer must be a single JSON object: "
    '{"steps": [{"title": "<what was checked and the outcome>", "source": "<input used>", '
    '"result": "pass" | "fail", "evidence": {<key facts>}}], '
    '"output": {"valid": true | false, '
    '"issues": [{"check": "<check>", "field": "<package field>", "expected": <value from the inputs>, "found": <value in the package>, '
    '"owner": "<agent whose output is wrong or missing>"}], '
    '"reason": "<one short sentence>"}, '
    '"confidence": <0.0-1.0, how sure you are of the verdict>}. '
    "Return ONLY JSON — no preamble, no markdown fences."
)


async def output_validator_node(state: State, gateway: ModelGateway | None = None) -> dict:
    # it checks what is already in previous_results, so it never asks anyone
    return await run_stage_agent(
        "output-validator", 
        "execution", 
        "Output Validator", 
        state,
        gateway=gateway, 
        json_instruction=_JSON_INSTRUCTION, 
        asks=False,
    )
