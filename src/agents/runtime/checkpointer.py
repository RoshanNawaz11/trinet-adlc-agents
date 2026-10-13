"""One factory function so `graph/build.py` never imports a specific
checkpointer backend directly.

- `sqlite` (what the runner uses): runs survive a restart, so a run paused
  for review can be resumed by a later process. One file per run, in the
  run's folder (runtime/run_dir.py). Must be created inside a running event
  loop; close it with `close_checkpointer`.
- `memory`: gone when the graph is closed — fine for tests.
- `redis`: for several worker processes; a TODO until it is needed.
"""

from __future__ import annotations

from pathlib import Path

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import InMemorySaver


def get_checkpointer(kind: str = "memory", db_path: Path | None = None) -> BaseCheckpointSaver:
    if kind == "memory":
        return InMemorySaver()

    if kind == "sqlite":
        import aiosqlite
        from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

        if db_path is None:
            raise ValueError("the sqlite checkpointer needs the run's db_path")
        # connects lazily on first use (AsyncSqliteSaver.setup)
        return AsyncSqliteSaver(aiosqlite.connect(str(db_path)))

    if kind == "redis":
        # pip install langgraph-checkpoint-redis
        # from langgraph.checkpoint.redis import AsyncRedisSaver
        # return AsyncRedisSaver(REDIS_URL)
        raise NotImplementedError("redis checkpointer: add langgraph-checkpoint-redis and wire it in here")

    raise ValueError(f"Unknown checkpointer kind: {kind}")


async def close_checkpointer(saver: BaseCheckpointSaver | None) -> None:
    """Close the sqlite connection — its thread otherwise keeps the process alive."""
    conn = getattr(saver, "conn", None)
    if conn is not None:
        await conn.close()
