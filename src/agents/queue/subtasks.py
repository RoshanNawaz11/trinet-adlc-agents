"""The sub-task queue — one queue for every worker agent.
A specialist agent puts independent units of work on it, the worker pool
(pool.py, box 7) runs them, and each result comes back to the agent that
emitted it. Redis + arq.
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, NotRequired, TypedDict

from arq import create_pool
from arq.connections import RedisSettings

from agents.model.gateway import session_id

logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
QUEUE = "subtasks"
# how long an agent waits for one sub-task's result
RESULT_TIMEOUT = float(os.getenv("SUBTASK_TIMEOUT", "300"))


class SubTask(TypedDict):
    kind: str                   # the worker that runs it, e.g. "validation.identity" (pool.HANDLERS)
    input: dict[str, Any]       # everything the worker needs — workers hold no state
    session_id: NotRequired[str | None]  # the run it belongs to, so its model calls join the run's trace


def redis_settings() -> RedisSettings:
    return RedisSettings.from_dsn(REDIS_URL)


async def dispatch(tasks: list[SubTask]) -> list[dict[str, Any]]:
    """Put every task on the queue and wait for all the results, in task order.
    The workers run them in parallel. Each result is
    {"status": "done", "result": ...} or {"status": "failed", "error": ...}."""
    redis = await create_pool(redis_settings())
    try:
        sid = session_id.get()
        jobs = [await redis.enqueue_job("run_subtask", {**t, "session_id": sid}, _queue_name=QUEUE) for t in tasks]
        logger.info("[queue] %d sub-task(s) queued: %s", len(jobs), [t["kind"] for t in tasks])
        results = await asyncio.gather(
            *(j.result(timeout=RESULT_TIMEOUT, poll_delay=0.2) for j in jobs), return_exceptions=True,
        )
    finally:
        await redis.aclose()
    out: list[dict[str, Any]] = []
    for r in results:
        if isinstance(r, asyncio.TimeoutError):
            out.append({"status": "failed", "error": f"no result from the worker pool within {RESULT_TIMEOUT:.0f}s"})
        elif isinstance(r, BaseException):
            out.append({"status": "failed", "error": f"{type(r).__name__}: {r}"})
        else:
            out.append({"status": "done", "result": r})
    return out
