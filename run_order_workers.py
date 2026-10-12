"""Start the service-order worker: it pulls runs off the Redis queue
(REDIS_URL, default redis://localhost:6379, queue "service_orders") and runs
the agent graph for each one.

Run this next to ``run_workers.py`` (the sub-task pool) and the agents HTTP
server. The HTTP server is what FastAPI polls for step results; both processes
must share the same CHECKPOINT_DB.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from arq import run_worker

from agents.queue.orders import WorkerSettings
from agents.runtime.runner import _setup_logging

if __name__ == "__main__":
    _setup_logging()
    run_worker(WorkerSettings)
