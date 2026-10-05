"""Compliance's exceptions worker — a model. Spots cases that need a special
human decision: an active leave of absence or a garnishment (skills/compliance).

    input  {"case", "facts", "service_order", "data", "worker_results"}
    output {"case", "worker", "findings": {"exceptions": [...]}, "steps", "flags"}
"""

from __future__ import annotations

from typing import Any

from agents.workers import run_checker


async def exceptions(i: dict[str, Any]) -> dict[str, Any]:
    return await run_checker("compliance", "exceptions", i)
