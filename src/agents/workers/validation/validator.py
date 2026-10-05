"""Validation's validator worker — a model. Checks the facts are complete, make
sense together, agree with the records, and don't clash with other orders or
the pay calendar (skills/validation/workers/validator.md).

    input  {"case", "service_order", "data", "worker_results"}
    output {"case", "worker", "findings": {"missing_fields", "pay_cycle"}, "steps", "flags"}
"""

from __future__ import annotations

from typing import Any

from agents.workers import run_checker


async def validator(i: dict[str, Any]) -> dict[str, Any]:
    return await run_checker("validation", "validator", i)
