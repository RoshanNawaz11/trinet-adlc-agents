"""HTTP entrypoint: FastAPI polls run status here.

FastAPI enqueues a run onto the Redis ``service_orders`` queue
(``run_order_workers.py``) instead of calling ``POST /runs``. This server still
serves ``GET /runs/{thread_id}`` from the checkpointer, which is how the
dashboard sees steps finished so far. ``POST /runs`` and ``POST /resume``
remain for a manual run.

Runs started here execute as background tasks in this process. Their state is
in the checkpointer (sqlite by default), so a paused run survives a restart
and can still be read and resumed; a run that was mid-flight at the restart
is not restarted.

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
from typing import Any, Literal

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, model_validator

_SRC_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if _SRC_ROOT not in sys.path:
    sys.path.insert(0, _SRC_ROOT)

from agents.graph.edges import FLAG_REVIEW
from agents.graph.interrupts import missing_answers
from agents.graph.pipeline import with_pipeline
from agents.observability.langwatch_setup import langwatch_setup
from agents.runtime.runner import _setup_logging, open_graph, run_query

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


class ReviewDecision(BaseModel):
    """The reviewer's approval or rejection of the whole run (graph.states.Review)."""
    action: Literal["approve", "reject"]
    reason: str | None = None

    @model_validator(mode="after")
    def _reason_on_reject(self) -> "ReviewDecision":
        if self.action == "reject" and not self.reason:
            raise ValueError("a reject needs a reason")
        return self


class FlagAnswer(BaseModel):
    """The analyst's answer to one flag: accept its suggested fix, or decline it
    and type the answer instead."""
    flag_id: str
    action: Literal["accept", "decline"]
    answer: str | None = None   # what the analyst typed; required on decline

    @model_validator(mode="after")
    def _typed_on_decline(self) -> "FlagAnswer":
        if self.action == "decline" and not (self.answer or "").strip():
            raise ValueError(f"declining {self.flag_id} needs the analyst's answer")
        return self


class FlagAnswers(BaseModel):
    """The analyst's answers to every flag the run is paused on (graph.interrupts.flag_review_node)."""
    answers: list[FlagAnswer]


@asynccontextmanager
async def _lifespan(_: FastAPI):
    _setup_logging()
    langwatch_setup()
    yield


app = FastAPI(title="trinet-agents", lifespan=_lifespan)


async def _snapshot(thread_id: str):
    """The run's latest state, read from its own checkpointer."""
    async with open_graph(thread_id) as graph:
        return await graph.aget_state({"configurable": {"thread_id": thread_id}})


def _publish(payload: dict[str, Any]) -> dict[str, Any]:
    """Every payload the console reads carries the pipeline stages."""
    if isinstance(payload.get("values"), dict):
        return {**payload, "values": with_pipeline(payload["values"])}
    return payload


async def _execute(
    thread_id: str, req: RunRequest | None, resume: bool, decision: dict[str, Any] | None = None
) -> None:
    try:
        out = await run_query(
            req.query if req else "",
            service_order_id=req.service_order_id if req else None,
            thread_id=thread_id,
            resume=resume,
            decision=decision,
        )
        _runs[thread_id] = _publish({**out, "status": "paused" if out.get("paused") else "done"})
    except Exception as exc:
        logger.exception("Run %s failed", thread_id)
        _runs[thread_id] = {"thread_id": thread_id, "status": "failed", "error": str(exc)}


def _start(
    thread_id: str, req: RunRequest | None, resume: bool, decision: dict[str, Any] | None = None
) -> dict[str, Any]:
    _runs[thread_id] = {"thread_id": thread_id, "status": "running"}
    task = asyncio.create_task(_execute(thread_id, req, resume, decision))
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
async def resume_run(thread_id: str, decision: FlagAnswers | ReviewDecision) -> dict[str, Any]:
    if _runs.get(thread_id, {}).get("status") == "running":
        raise HTTPException(409, f"Run {thread_id} is running")
    # the checkpointer, not _runs, says whether it is paused — it outlives a restart
    snapshot = await _snapshot(thread_id)
    if not snapshot.next:
        raise HTTPException(409, f"Run {thread_id} is not paused")
    on_flags = FLAG_REVIEW in snapshot.next
    if on_flags != isinstance(decision, FlagAnswers):
        expected = "the answers to its flags" if on_flags else "approve or reject"
        raise HTTPException(422, f"Run {thread_id} is paused at {list(snapshot.next)} — send {expected}")
    body = decision.model_dump(exclude_none=True)
    if on_flags and (missing := missing_answers(snapshot.values or {}, body)):
        raise HTTPException(422, f"Answer every flag before the case continues — no answer yet for {missing}")
    return _start(thread_id, None, resume=True, decision=body)


@app.get("/runs/{thread_id}")
async def get_run(thread_id: str) -> dict[str, Any]:
    run = _runs.get(thread_id)
    # A finished payload already carries its values. A running or failed run
    # does not: those live in the checkpointer, written after every node.
    if run and run["status"] not in ("running", "failed") and "values" in run:
        return _publish(run)
    snapshot = await _snapshot(thread_id)
    if not snapshot.values:
        if run:
            return _publish(run)
        raise HTTPException(404, f"Unknown run {thread_id}")
    if run:
        return _publish({**run, "values": snapshot.values})
    return _publish({
        "thread_id": thread_id,
        "status": "paused" if snapshot.next else "done",
        "paused": bool(snapshot.next),
        "next": list(snapshot.next),
        "values": snapshot.values,
        "pending": [i.value for i in snapshot.interrupts],
    })


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("AGENTS_PORT", "8100")))
