"""Start the worker pool: it pulls sub-tasks off the Redis queue (REDIS_URL,
default redis://localhost:6379) and runs them.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from arq import run_worker

from agents.queue.pool import WorkerSettings
from agents.runtime.runner import _setup_logging

if __name__ == "__main__":
    _setup_logging()
    run_worker(WorkerSettings)
