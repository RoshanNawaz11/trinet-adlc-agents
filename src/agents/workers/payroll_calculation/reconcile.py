"""Payroll's reconcile worker — a model. Runs after earnings, leave and
deductions: puts final pay together and checks it against the payroll system
and the payment method (skills/payroll-calculation/workers/reconcile.md).

    input  {"case", "facts", "service_order", "data", "worker_results": [<round 1's results>]}
    output {"case", "worker", "findings": {"taxes", "unrecoverable", "net_pay", ...}, "steps", "flags"}
"""

from __future__ import annotations

from typing import Any

from agents.workers import run_checker


async def reconcile(i: dict[str, Any]) -> dict[str, Any]:
    return await run_checker("payroll-calculation", "reconcile", i)
