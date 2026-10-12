"""The service-order queue.

FastAPI puts one job here per processing run (and a second job to resume a
run paused for review). This worker runs the agent graph. The sub-task queue
(subtasks.py) is separate on purpose: a service-order job waits on its
sub-tasks, so the two must not share a worker pool.

Status for a run is a Redis key, ``order-run:{thread_id}``, holding
``{"status": "queued|running|paused|done|failed", "error": "..."}``.
FastAPI writes ``queued`` when it enqueues; this worker writes the rest.
The key and the JSON shape are the contract with fastapi-backend's
``app/clients/order_queue.py`` — keep the two in step.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from agents.observability.langwatch_setup import langwatch_setup
from agents.queue.subtasks import redis_settings
from agents.runtime.runner import close_graph, run_query

logger = logging.getLogger(__name__)

QUEUE = "service_orders"
STATUS_TTL_SECONDS = 7 * 24 * 3600


def status_key(thread_id: str) -> str:
    return f"order-run:{thread_id}"


async def write_status(
    redis: Any, thread_id: str, status: str, error: str | None = None
) -> None:
    payload: dict[str, str] = {"status": status}
    if error:
        payload["error"] = error
    await redis.set(status_key(thread_id), json.dumps(payload), ex=STATUS_TTL_SECONDS)


async def _run(ctx: dict, job: dict, *, resume: bool) -> dict[str, Any]:
    thread_id = job["thread_id"]
    await write_status(ctx["redis"], thread_id, "running")
    try:
        out = await run_query(
            job.get("query") or "",
            service_order_id=job.get("service_order_id"),
            thread_id=thread_id,
            resume=resume,
            decision=job.get("decision"),
        )
    except Exception as exc:
        logger.exception("Service order run %s failed", thread_id)
        await write_status(ctx["redis"], thread_id, "failed", error=str(exc))
        return {"thread_id": thread_id, "status": "failed", "error": str(exc)}

    status = "paused" if out.get("paused") else "done"
    await write_status(ctx["redis"], thread_id, status)
    return {**out, "status": status}


async def process_service_order(ctx: dict, job: dict) -> dict[str, Any]:
    """Start a run. ``job`` is ``{"thread_id", "query"}``."""
    logger.info("[orders] start %s", job.get("thread_id"))
    return await _run(ctx, job, resume=False)


async def resume_service_order(ctx: dict, job: dict) -> dict[str, Any]:
    """Continue a run paused for review. ``job`` is ``{"thread_id", "decision"}``."""
    logger.info("[orders] resume %s", job.get("thread_id"))
    return await _run(ctx, job, resume=True)


async def startup(ctx: dict) -> None:
    langwatch_setup()


async def shutdown(ctx: dict) -> None:
    await close_graph()


class WorkerSettings:
    functions = [process_service_order, resume_service_order]
    queue_name = QUEUE
    redis_settings = redis_settings()
    on_startup = startup
    on_shutdown = shutdown
    # One service order holds its worker until the graph finishes, including
    # while that graph waits on the sub-task pool. Keep this small.
    max_jobs = int(os.getenv("ORDER_WORKER_CONCURRENCY", "2"))
    job_timeout = int(os.getenv("ORDER_JOB_TIMEOUT", "900"))
    # A redelivery would re-run the model calls. A crashed job stays failed;
    # the service order can be processed again as a new run.
    max_tries = 1
