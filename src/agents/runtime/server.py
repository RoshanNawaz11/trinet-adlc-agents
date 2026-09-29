"""HTTP entrypoint: the FastAPI backend submits runs here and polls their status.

Runs execute as background tasks in this process. Run status lives in memory,
like the default checkpointer, so a restart forgets in-flight and paused runs.
Swapping `_start` for a queue enqueue later doesn't change the HTTP contract.

    uv run src/agents/runtime/server.py
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, model_validator

_SRC_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if _SRC_ROOT not in sys.path:
    sys.path.insert(0, _SRC_ROOT)

from agents.observability.langwatch_setup import langwatch_setup
from agents.runtime.runner import _setup_logging, get_graph, run_query

logger = logging.getLogger(__name__)

_runs: dict[str, dict[str, Any]] = {}
_tasks: set[asyncio.Task] = set()  # keeps background tasks from being garbage-collected


class RunRequest(BaseModel):
    service_order_id: str | None = None  # preferred: the agents fetch the order themselves
    query: str = ""                      # fallback: the order described as text
    thread_id: str | None = None

    @model_validator(mode="after")
    def _one_input(self) -> "RunRequest":
        if not self.service_order_id and not self.query:
            raise ValueError("send service_order_id (or, as a fallback, query)")
        return self


@asynccontextmanager
async def _lifespan(_: FastAPI):
    _setup_logging()
    langwatch_setup()
    yield


app = FastAPI(title="trinet-agents", lifespan=_lifespan)


async def _execute(thread_id: str, req: RunRequest | None, resume: bool) -> None:
    try:
        out = await run_query(
            req.query if req else "",
            service_order_id=req.service_order_id if req else None,
            thread_id=thread_id,
            resume=resume,
        )
        _runs[thread_id] = {**out, "status": "paused" if out.get("paused") else "done"}
    except Exception as exc:
        logger.exception("Run %s failed", thread_id)
        _runs[thread_id] = {"thread_id": thread_id, "status": "failed", "error": str(exc)}


def _start(thread_id: str, req: RunRequest | None, resume: bool) -> dict[str, Any]:
    _runs[thread_id] = {"thread_id": thread_id, "status": "running"}
    task = asyncio.create_task(_execute(thread_id, req, resume))
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)
    return _runs[thread_id]


@app.post("/runs", status_code=202)
async def create_run(req: RunRequest) -> dict[str, Any]:
    thread_id = req.thread_id or str(uuid.uuid4())
    if _runs.get(thread_id, {}).get("status") in ("running", "paused"):
        raise HTTPException(409, f"Run {thread_id} is already {_runs[thread_id]['status']}")
    return _start(thread_id, req, resume=False)


@app.post("/runs/{thread_id}/resume", status_code=202)
async def resume_run(thread_id: str) -> dict[str, Any]:
    if _runs.get(thread_id, {}).get("status") != "paused":
        raise HTTPException(409, f"Run {thread_id} is not paused")
    return _start(thread_id, None, resume=True)


@app.get("/runs/{thread_id}")
async def get_run(thread_id: str) -> dict[str, Any]:
    if thread_id not in _runs:
        raise HTTPException(404, f"Unknown run {thread_id}")
    run = _runs[thread_id]
    if run["status"] == "running":
        # LangGraph checkpoints after every node, so this is everything done
        # so far — plan, steps, flags, priority, confidence — for live progress
        snapshot = await get_graph().aget_state({"configurable": {"thread_id": thread_id}})
        return {**run, "values": snapshot.values}
    return run


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("AGENTS_PORT", "8100")))
