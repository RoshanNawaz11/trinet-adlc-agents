"""Payroll's leave worker — a model. Decides whether unused leave is paid out
with final pay, and how much (skills/payroll-calculation/workers/leave.md).

    input  {"case", "facts", "service_order", "data", "worker_results"}
    output {"case", "worker", "findings": {"leave_payout", "leave_hours", "pto_payout"}, "steps", "flags"}
"""

from __future__ import annotations

from typing import Any

from agents.workers import run_checker


async def leave(i: dict[str, Any]) -> dict[str, Any]:
    return await run_checker("payroll-calculation", "leave", i)
