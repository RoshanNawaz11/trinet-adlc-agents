"""The business pipeline the console renders.

The UI does not invent these stages. Every run carries this list, and a step
or flag is placed by matching its agent name, then its stage, against the
names below. Agents keep doing their own work; this only says which pipeline
stage that work belongs to.
"""

from __future__ import annotations

from typing import Any

# Order is the pipeline order, and the order the orchestrator runs the agents
# in. `agents` are graph node names and the display names those nodes write
# onto a step. `stages` are StepRecord.stage values. A listed agent wins over
# `stages`. Orchestrator routing steps and the reviewer's own step belong to no
# stage: the review is the final decision after the last stage, not a stage.
PIPELINE: list[dict[str, Any]] = [
    {
        "key": "validation",
        "label": "SO Validation",
        "agents": ["planner", "validation", "Planner", "Validation Agent"],
        "stages": ["validation"],
    },
    {
        "key": "payroll",
        "label": "Payroll Calculation",
        "agents": ["payroll-calculation", "payroll", "Payroll Calculation Agent"],
        "stages": ["payroll"],
    },
    {
        "key": "audit",
        "label": "Audit & Review",
        "agents": ["compliance", "Compliance Agent"],
        "stages": ["compliance"],
    },
    {
        "key": "distribution",
        "label": "Distribution Info",
        "agents": ["execution", "Execution Agent"],
        "stages": ["execution"],
    },
]


def with_pipeline(values: dict[str, Any] | None) -> dict[str, Any]:
    """The run state with the current pipeline, so a checkpoint written before a
    change to the stages still renders with the stages as they are now."""
    return {**(values or {}), "pipeline": PIPELINE}
