"""Payroll's earnings worker — a model. Works out regular pay, overtime and gross
pay for the final period (skills/payroll-calculation/workers/earnings.md).

    input  {"case", "facts", "service_order", "data", "worker_results"}
    output {"case", "worker", "findings": {"regular_pay", "overtime_pay", "gross_pay", ...}, "steps", "flags"}
"""

from __future__ import annotations

from typing import Any

from agents.workers import run_checker


async def earnings(i: dict[str, Any]) -> dict[str, Any]:
    return await run_checker("payroll-calculation", "earnings", i)
