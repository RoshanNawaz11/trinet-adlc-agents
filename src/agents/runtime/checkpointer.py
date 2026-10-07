"""One factory function so `graph/build.py` never imports a specific
checkpointer backend directly.

- `sqlite` (what the runner uses): runs survive a restart, so a run paused
  for review can be resumed by a later process. File: CHECKPOINT_DB, default
  `checkpoints/checkpoints.db`. The folder is created if it is missing. Must be
  created inside a running event loop; close it with `close_checkpointer`.
- `memory`: gone when the process exits — fine for tests.
- `redis`: for several worker processes; a TODO until it is needed.
"""

from __future__ import annotations

import os
from pathlib import Path

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import InMemorySaver

_DEFAULT_DB = Path(__file__).resolve().parents[3] / "checkpoints" / "checkpoints.db"


def get_checkpointer(kind: str = "memory") -> BaseCheckpointSaver:
    if kind == "memory":
        return InMemorySaver()

    if kind == "sqlite":
        import aiosqlite
        from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

        # connects lazily on first use (AsyncSqliteSaver.setup)
        db_path = Path(os.getenv("CHECKPOINT_DB", str(_DEFAULT_DB)))
        db_path.parent.mkdir(parents=True, exist_ok=True)
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
