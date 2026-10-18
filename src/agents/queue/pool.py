"""The worker pool: N identical, stateless workers pull
sub-tasks from the one sub-task queue and return results to the agent that
emitted them. Start it next to the agents:

    uv run run_workers.py

A worker agent joins the pool with one line in HANDLERS.
"""

from __future__ import annotations

import inspect
import logging
import os
from typing import Any

from agents.model.gateway import session_id
from agents.queue.subtasks import QUEUE, SubTask, redis_settings
from agents.workers.compliance.obligations import obligations
from agents.workers.compliance.timing import timing
from agents.workers.payroll_calculation.deductions import deductions
from agents.workers.payroll_calculation.earnings import earnings
from agents.workers.payroll_calculation.leave import leave
from agents.workers.payroll_calculation.reconcile import reconcile
from agents.workers.validation.extractor import extract
from agents.workers.validation.identity import identity
from agents.workers.validation.validator import validator

logger = logging.getLogger(__name__)

# sub-task kind -> the worker that runs it
HANDLERS = {
    "validation.extract": extract,
    "validation.identity": identity,
    "validation.validator": validator,
    "compliance.timing": timing,
    "compliance.obligations": obligations,
    "payroll-calculation.earnings": earnings,
    "payroll-calculation.leave": leave,
    "payroll-calculation.deductions": deductions,
    "payroll-calculation.reconcile": reconcile,
}


async def run_subtask(ctx: dict, task: SubTask) -> Any:
    logger.info("[worker] %s %s", task["kind"], task["input"].get("case", ""))
    # each job runs in its own asyncio task, so this only affects this job's model calls
    session_id.set(task.get("session_id"))
    result = HANDLERS[task["kind"]](task["input"])
    return await result if inspect.isawaitable(result) else result


class WorkerSettings:
    functions = [run_subtask]
    queue_name = QUEUE
    redis_settings = redis_settings()
    max_jobs = int(os.getenv("WORKER_CONCURRENCY", "10"))  # sub-tasks one pool process runs at once
    job_timeout = 300
