"""Each run's folder: logs/<date>_<service order>_<id>/ holds its agents.log,
workers.log and checkpoint.db."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

LOG_DIR = Path(__file__).resolve().parents[3] / "logs"


def run_dir(thread_id: str, service_order_id: str | None = None) -> Path:
    """The run's folder, found by its thread id — so a resume and the worker
    processes use the folder the run started in. A new run gets a new one."""
    short = thread_id[:8]
    found = next(LOG_DIR.glob(f"*_{short}"), None)
    if found is None:
        found = LOG_DIR / f"{datetime.now():%Y-%m-%d_%H%M}_{service_order_id or 'run'}_{short}"
        found.mkdir(parents=True, exist_ok=True)
    return found
