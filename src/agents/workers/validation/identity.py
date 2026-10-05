"""Validation's identity worker — a model. Checks the order is open and is about
a real employee of this company who can still be processed
(skills/validation/workers/identity.md).

    input  {"case", "universal": bool, "service_order", "data", "worker_results"}
    output {"case", "worker", "findings": {"subject_employee_id", "subject_name", "work_state"}, "steps", "flags"}
"""

from __future__ import annotations

from typing import Any

from agents.workers import run_checker


async def identity(i: dict[str, Any]) -> dict[str, Any]:
    return await run_checker("validation", "identity", i)
