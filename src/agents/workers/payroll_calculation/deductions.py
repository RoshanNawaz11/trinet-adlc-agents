"""Payroll's deductions worker — a model. Works out benefits eligibility, the
deductions and garnishments taken from final pay, and what the client is billed
instead (skills/payroll-calculation/workers/deductions.md).

    input  {"case", "facts", "service_order", "data", "worker_results"}
    output {"case", "worker", "findings": {"benefits_eligible", "deductions", "garnishments", ...}, "steps", "flags"}
"""

from __future__ import annotations

from typing import Any

from agents.workers import run_checker


async def deductions(i: dict[str, Any]) -> dict[str, Any]:
    return await run_checker("payroll-calculation", "deductions", i)
