"""Emit agent progress to FastAPI. FastAPI is the only writer to Postgres.

After each node the graph POSTs the new steps, flags, and run status. FastAPI
persists them through its repositories so the UI can read Recent Activity and
the Audit Log without this service knowing the table shape.
"""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

_STAGE_TONE = {
    "compliance": "amber",
    "payroll": "grey",
    "execution": "green",
}

# who raised a flag, by the stage it belongs to
_STAGE_AGENT = {
    "planning": "Orchestrator",
    "validation": "Validation Agent",
    "compliance": "Compliance Agent",
    "payroll": "Payroll Calculation Agent",
    "execution": "Execution Agent",
}

_FEED_KINDS = {"attention", "handoff", "routine"}


def _backend_url() -> str:
    return os.getenv("BACKEND_URL", "http://127.0.0.1:8000").rstrip("/")


def employee_name(service_order: dict[str, Any] | None) -> str | None:
    if not service_order:
        return None
    subject = service_order.get("subjectEmployee") or service_order.get("subject_employee") or {}
    if not isinstance(subject, dict):
        return None
    return subject.get("fullName") or subject.get("full_name")


def _clip(value: str, limit: int = 255) -> str:
    return value if len(value) <= limit else value[: limit - 1] + "…"


def _display(name: str | None, text: str) -> str:
    return f"{name} — {text}" if name else text


def events_from_update(
    update: dict[str, Any], *, employee: str | None
) -> list[dict[str, Any]]:
    """Map a node's state onto the FastAPI ingest event shape."""
    events: list[dict[str, Any]] = []
    for step in update.get("steps") or []:
        if not isinstance(step, dict) or not step.get("title"):
            continue
        title = str(step["title"])
        at = str(step.get("at") or title)
        events.append(
            {
                "dedupe_key": _clip(f"step:{at}:{title}"),
                "title": _clip(_display(employee, title)),
                "action": _clip(title),
                "actor": _clip(str(step.get("agent") or "AI Agents"), 128),
                "system": _clip(str(step.get("source") or "Agents"), 128),
                "kind": "agent",
                "tone": _STAGE_TONE.get(str(step.get("stage") or ""), "blue"),
                "employee_name": employee,
                "feed_kind": step.get("feed") if step.get("feed") in _FEED_KINDS else None,
            }
        )
    for flag in update.get("flags") or []:
        if not isinstance(flag, dict) or flag.get("resolved") or not flag.get("title"):
            continue
        title = str(flag["title"])
        flag_id = str(flag.get("flag_id") or title)
        events.append(
            {
                "dedupe_key": _clip(f"flag:{flag_id}"),
                "title": _clip(_display(employee, title)),
                "action": _clip(title),
                "actor": _STAGE_AGENT.get(str(flag.get("stage") or ""), "AI Agents"),
                "system": "Agents",
                "kind": "agent",
                "tone": "amber",
                "employee_name": employee,
                "feed_kind": "attention",
            }
        )
    return events


def lifecycle_event(kind: str, *, employee: str | None) -> dict[str, Any]:
    catalog = {
        "started": ("Processing started", "Started processing", "AI Agents", "agent", "blue", None),
        "paused": ("Ready for Mark as Reviewed", "Paused for analyst review", "AI Agents", "agent", "green", "attention"),
        "completed": ("Review completed", "Completed review", "AI Agents", "agent", "green", "routine"),
        "needs_review": ("Flagged for review", "Flagged for review", "AI Agents", "agent", "amber", "attention"),
        "failed": ("Processing failed", "Processing failed", "System", "system", "red", "attention"),
    }
    title, action, actor, event_kind, tone, feed_kind = catalog[kind]
    return {
        "dedupe_key": f"lifecycle:{kind}",
        "title": _clip(_display(employee, title.lower()) if employee else title),
        "action": action,
        "actor": actor,
        "system": "Agents",
        "kind": event_kind,
        "tone": tone,
        "employee_name": employee,
        "feed_kind": feed_kind,
    }


async def report_progress(
    thread_id: str,
    *,
    update: dict[str, Any] | None = None,
    run_status: str | None = None,
    error: str | None = None,
    employee: str | None = None,
    extra_events: list[dict[str, Any]] | None = None,
    service_order_no: str | None = None,
) -> None:
    # service_order_no is accepted for callers; FastAPI resolves the order from the run.
    events = list(extra_events or [])
    if update:
        events.extend(events_from_update(update, employee=employee))
    payload = {
        "events": events,
        "values": update,
        "run_status": run_status,
        "error": error,
    }
    url = f"{_backend_url()}/api/v1/processing-runs/{thread_id}/events"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(url, json=payload)
        if response.status_code >= 400:
            logger.warning(
                "backend progress %s -> HTTP %s %s",
                thread_id,
                response.status_code,
                response.text[:300],
            )
    except httpx.HTTPError as exc:
        logger.warning("backend progress %s failed: %s", thread_id, exc)
