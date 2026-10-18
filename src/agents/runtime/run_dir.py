"""Each run's folder: logs/<date>_<order name>_<order id>_<id>/ holds its
agents.log, workers.log and checkpoint.db."""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Any

LOG_DIR = Path(__file__).resolve().parents[3] / "logs"


def _slug(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "-", text).strip("-")[:40]


def run_dir(thread_id: str, service_order: dict[str, Any] | None = None) -> Path:
    """The run's folder, found by its thread id — so a resume and the worker
    processes use the folder the run started in. A new run gets a new one,
    named after its service order. A folder made before the order was known
    (e.g. by a status check while the run waited in the queue) is renamed."""
    short = thread_id[:8]
    labels = [_slug(str(service_order.get(k) or "")) for k in ("name", "soId")] if service_order else []
    labels = [label for label in labels if label] or ["run"]
    found = next(LOG_DIR.glob(f"*_{short}"), None)
    if found is not None and (labels == ["run"] or not found.name.endswith(f"_run_{short}")):
        return found
    named = LOG_DIR / "_".join([f"{datetime.now():%Y-%m-%d_%H%M}", *labels, short])
    if found is None:
        named.mkdir(parents=True, exist_ok=True)
        return named
    try:
        return found.rename(named)
    except OSError:  # still open in another process — keep the name it has
        return found
