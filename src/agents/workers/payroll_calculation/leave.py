"""Payroll's leave worker — a model. Applies payroll.leave-payout: whether unused
leave is paid out with final pay, and how much (skills/payroll-calculation/workers/leave.md).

    input  {"case", "facts", "service_order", "data", "worker_results", "rules"}
    output {"case", "worker", "findings": {"leave_payout", "provisional", "leave_lines"}, "steps", "flags"}
"""

from __future__ import annotations

from typing import Any

from agents.workers import run_checker


async def leave(i: dict[str, Any]) -> dict[str, Any]:
    return await run_checker("payroll-calculation", "leave", i)
