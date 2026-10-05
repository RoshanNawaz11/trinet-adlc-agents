"""Compliance's obligations worker — a model. Works out what the rules require
beyond pay timing: unused PTO payout and COBRA notices (skills/compliance).

    input  {"case", "facts", "service_order", "data", "worker_results"}
    output {"case", "worker", "findings": {"pto_payout", "cobra", ...}, "steps", "flags"}
"""

from __future__ import annotations

from typing import Any

from agents.workers import run_checker


async def obligations(i: dict[str, Any]) -> dict[str, Any]:
    return await run_checker("compliance", "obligations", i)
