"""Runs the agent graph: builds it once, starts a run for a service order and
resumes a paused one. Used by the HTTP server and as a CLI.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from langgraph.types import Command
from langwatch.telemetry.context import get_current_trace
_SRC_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if _SRC_ROOT not in sys.path:
    sys.path.insert(0, _SRC_ROOT)

from agents.graph.build import build_graph
from agents.graph.pipeline import PIPELINE
from agents.model.gateway import session_id, trace_id
from agents.runtime.checkpointer import close_checkpointer
from agents.runtime.idempotency import already_processed, idempotency_key, mark_processed
from agents.runtime.run_dir import LOG_DIR, run_dir
from agents.tools.mcp_client import call_mcp_tool, mcp_client
from agents.tools.scopes import MCP_SERVER
from agents.observability.langwatch_setup import langwatch_setup
from agents.observability.tracing import attach_metadata, maybe_trace

class _RunLogs(logging.Handler):
    """Each run's records go to <process>.log in the run's folder; the rest to
    logs/<process>.log."""

    def __init__(self, process: str) -> None:
        super().__init__(logging.DEBUG)
        self._file = f"{process}.log"
        self._paths: dict[str | None, Path] = {None: LOG_DIR / self._file}

    def emit(self, record: logging.LogRecord) -> None:
        run = session_id.get()
        try:
            if run not in self._paths:
                self._paths[run] = run_dir(run) / self._file
            with self._paths[run].open("a", encoding="utf-8") as f:
                f.write(self.format(record) + "\n")
        except Exception:
            self.handleError(record)


def _setup_logging(process: str = "agents") -> None:
    """`process` names the log file: agents.log, or workers.log in the worker pool."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    logging.getLogger("aiosqlite").setLevel(logging.INFO)  # a DEBUG line per sqlite call

    fmt = logging.Formatter("%(asctime)s %(levelname)-7s %(name)s: %(message)s")

    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(fmt)
    root.addHandler(console)

    run_logs = _RunLogs(process)
    run_logs.setFormatter(fmt)
    root.addHandler(run_logs)


@asynccontextmanager
async def open_graph(thread_id: str):
    """The graph with the run's own checkpointer, built inside the running
    event loop, which the sqlite checkpointer needs. CHECKPOINTER=memory|sqlite
    (default sqlite: checkpoint.db in the run's folder)."""
    graph = build_graph(os.getenv("CHECKPOINTER", "sqlite"), run_dir(thread_id) / "checkpoint.db")
    try:
        yield graph
    finally:
        await close_checkpointer(graph.checkpointer)


async def fetch_service_order(so_id: str) -> dict[str, Any]:
    """The service order record, fetched in code so every run starts from the
    real order rather than a text description of it."""
    if not MCP_SERVER:
        raise RuntimeError("MCP_SERVER is not set — needed to fetch the service order")
    async with mcp_client("runner") as mcp:
        data = await call_mcp_tool(mcp, "get_service_order", so_id=so_id)
    record = data.get("serviceOrder") if isinstance(data, dict) else None
    if not record:
        raise LookupError(f"Service order {so_id} not found")
    return record


def _initial_state(
    run_id: str, query: str, service_order_id: str | None, service_order: dict[str, Any] | None
) -> dict[str, Any]:
    state: dict[str, Any] = {
        "schema_version": 1,
        "run_id": run_id,
        "status": "running",
        "flagged": False,
        "results": {},
        "steps": [],
        "flags": [],
        "needs": [],
        "runs": {},
        "pipeline": PIPELINE,
    }
    if service_order is not None:
        state |= {"service_order_id": service_order_id, "service_order": service_order}
    else:
        state["query"] = query
    return state


def _config(thread_id: str) -> dict[str, Any]:
    config: dict[str, Any] = {"configurable": {"thread_id": thread_id}}
    # No agent-side trace when LANGWATCH_DISABLED=true — LiteLLM does the tracing.
    if os.getenv("LANGWATCH_DISABLED", "false").lower() != "true":
        config["callbacks"] = [get_current_trace().get_langchain_callback()]
    return config

@maybe_trace("run-agent-query")
async def run_query(
    query: str = "",
    *,
    service_order_id: str | None = None,
    thread_id: str | None = None,
    resume: bool = False,
    decision: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run the agents on a service order — by id (preferred: the record is
    fetched first) or, as a fallback, on a text description of it. On resume,
    `decision` is the reviewer's approval or rejection of the run (graph.states.Review)."""
    thread_id = thread_id or str(uuid.uuid4())
    run_dir(thread_id, service_order_id)  # the run's folder, named before anything logs to it
    session_id.set(thread_id)  # LiteLLM logs this as the session on every call of this run
    attach_metadata(thread_id=thread_id, resume=resume, service_order_id=service_order_id)
    config = _config(thread_id)
    key = idempotency_key(f"{thread_id}:{service_order_id or query}")

    async with open_graph(thread_id) as graph:
        if not resume and already_processed(key):
            snapshot = await graph.aget_state(config)
            return {
                "thread_id": thread_id,
                "trace_id": trace_id(thread_id),
                "skipped": True,
                "reason": "idempotent replay",
                "values": snapshot.values,
            }

        if resume:
            result = await graph.ainvoke(Command(resume=decision) if decision else None, config)
        else:
            # Guard against restarting a thread that's mid-run instead of
            # resuming it. A queue redelivery calling this without --resume
            # on a paused thread_id would otherwise silently re-invoke with
            # a fresh initial_state on top of existing checkpoint history —
            # and Worker's dispatch step calls non-idempotent live actions
            # (notify_on_call, create_ticket), so a silent restart risks
            # firing those twice.
            snapshot = await graph.aget_state(config)
            if snapshot.next:
                raise RuntimeError(
                    f"Thread {thread_id} is paused mid-run (next={list(snapshot.next)}) — "
                    "use --resume, not a fresh query, or you will restart instead of continue."
                )
            service_order = await fetch_service_order(service_order_id) if service_order_id else None
            result = await graph.ainvoke(
                _initial_state(thread_id, query, service_order_id, service_order), config
            )

        snapshot = await graph.aget_state(config)
    paused = bool(snapshot.next)
    if not paused:
        mark_processed(key)

    return {
        "thread_id": thread_id,
        "trace_id": trace_id(thread_id),
        "paused": paused,
        "next": list(snapshot.next) if paused else [],
        "values": result if result is not None else snapshot.values,
    }


async def _cli(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the agent graph for a service order.")
    parser.add_argument("service_order_id", nargs="?", help="Service order id, e.g. SO-1003.")
    parser.add_argument("--thread-id", dest="thread_id", default=None)
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume a thread paused for review, with --approve or --reject.",
    )
    review = parser.add_mutually_exclusive_group()
    review.add_argument("--approve", action="store_true", help="Approve the run: execution builds the package.")
    review.add_argument("--reject", metavar="REASON", help="Reject the run, with a reason: it ends.")
    args = parser.parse_args(argv)

    if args.resume and not args.thread_id:
        parser.error("--resume requires --thread-id")
    if args.resume and not args.approve and args.reject is None:
        parser.error("--resume requires --approve or --reject REASON")
    if not args.resume and not args.service_order_id:
        parser.error("a service order id is required unless --resume")

    decision = None
    if args.reject is not None:
        decision = {"action": "reject", "reason": args.reject}
    elif args.approve:
        decision = {"action": "approve"}

    out = await run_query(
        service_order_id=args.service_order_id, thread_id=args.thread_id,
        resume=args.resume, decision=decision,
    )
    print(json.dumps(out, default=str, indent=2))
    return 0


def main() -> None:
    _setup_logging()
    langwatch_setup()
    raise SystemExit(asyncio.run(_cli()))


if __name__ == "__main__":
    main()