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
from agents.runtime.backend import employee_name, lifecycle_event, report_progress
from agents.runtime.checkpointer import close_checkpointer
from agents.runtime.idempotency import already_processed, idempotency_key, mark_processed
from agents.tools.mcp_client import call_mcp_tool, mcp_client
from agents.tools.scopes import MCP_SERVER
from agents.observability.langwatch_setup import langwatch_setup
from agents.observability.tracing import attach_metadata, maybe_trace

_graph = None
_LOG_DIR = Path(__file__).resolve().parent.parent.parent.parent / "logs"


def _setup_logging() -> None:

    _LOG_DIR.mkdir(parents=True, exist_ok=True)
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    fmt = logging.Formatter("%(asctime)s %(levelname)-7s %(name)s: %(message)s")

    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console.setFormatter(fmt)
    root.addHandler(console)

    file_handler = logging.FileHandler(_LOG_DIR / "agents.log", encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(fmt)
    root.addHandler(file_handler)


def get_graph():
    """The graph, built on first use — inside the running event loop, which
    the sqlite checkpointer needs. CHECKPOINTER=memory|sqlite (default sqlite)."""
    global _graph
    if _graph is None:
        _graph = build_graph(os.getenv("CHECKPOINTER", "sqlite"))
    return _graph


async def close_graph() -> None:
    global _graph
    if _graph is not None:
        await close_checkpointer(_graph.checkpointer)
        _graph = None


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
    graph = get_graph()
    thread_id = thread_id or str(uuid.uuid4())
    session_id.set(thread_id)  # LiteLLM logs this as the session on every call of this run
    attach_metadata(thread_id=thread_id, resume=resume, service_order_id=service_order_id)
    config = _config(thread_id)
    key = idempotency_key(f"{thread_id}:{service_order_id or query}")

    if not resume and already_processed(key):
        snapshot = await graph.aget_state(config)
        return {
            "thread_id": thread_id,
            "trace_id": trace_id(thread_id),
            "skipped": True,
            "reason": "idempotent replay",
            "values": snapshot.values,
        }

    employee = None
    if resume:
        payload: Any = Command(resume=decision) if decision else None
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
        employee = employee_name(service_order)
        payload = _initial_state(thread_id, query, service_order_id, service_order)
        await report_progress(
            thread_id,
            run_status="running",
            employee=employee,
            extra_events=[lifecycle_event("started", employee=employee)],
            service_order_no=service_order_id,
        )

    try:
        async for _chunk in graph.astream(payload, config, stream_mode="updates"):
            live = await graph.aget_state(config)
            values = live.values if isinstance(live.values, dict) else {}
            if employee is None:
                employee = employee_name(values.get("service_order"))
            await report_progress(
                thread_id,
                update=values,
                run_status="running",
                employee=employee,
                service_order_no=service_order_id,
            )
    except Exception as exc:
        await report_progress(
            thread_id,
            run_status="failed",
            error=str(exc),
            employee=employee,
            extra_events=[lifecycle_event("failed", employee=employee)],
            service_order_no=service_order_id,
        )
        raise

    snapshot = await graph.aget_state(config)
    paused = bool(snapshot.next)
    values = snapshot.values or {}
    if employee is None:
        employee = employee_name(values.get("service_order") if isinstance(values, dict) else None)
    if not paused:
        mark_processed(key)
        verdict = values.get("status") if isinstance(values, dict) else None
        kind = "needs_review" if verdict == "needs_review" else "completed"
        await report_progress(
            thread_id,
            update=values if isinstance(values, dict) else None,
            run_status="done",
            employee=employee,
            extra_events=[lifecycle_event(kind, employee=employee)],
            service_order_no=service_order_id,
        )
    else:
        await report_progress(
            thread_id,
            update=values if isinstance(values, dict) else None,
            run_status="paused",
            employee=employee,
            extra_events=[lifecycle_event("paused", employee=employee)],
            service_order_no=service_order_id,
        )

    return {
        "thread_id": thread_id,
        "trace_id": trace_id(thread_id),
        "paused": paused,
        "next": list(snapshot.next) if paused else [],
        "values": values,
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

    try:
        out = await run_query(
            service_order_id=args.service_order_id, thread_id=args.thread_id,
            resume=args.resume, decision=decision,
        )
    finally:
        await close_graph()
    print(json.dumps(out, default=str, indent=2))
    return 0


def main() -> None:
    _setup_logging()
    langwatch_setup()
    raise SystemExit(asyncio.run(_cli()))


if __name__ == "__main__":
    main()