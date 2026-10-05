"""Compliance's timing worker — a model. Turns the rules into deadlines and
checks payroll can meet them: the legal due dates, the standard pay date, the
timing conflict and the payroll/bank cut-offs (skills/compliance).

    input  {"case", "facts", "service_order", "data", "worker_results"}
    output {"case", "worker", "findings": {<due dates>, "pay_timing", "submit_by", ...}, "steps", "flags"}
"""

from __future__ import annotations

from typing import Any

from agents.workers import run_checker


async def timing(i: dict[str, Any]) -> dict[str, Any]:
    return await run_checker("compliance", "timing", i)
