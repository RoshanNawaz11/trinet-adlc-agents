"""One factory function so `graph/build.py` never imports a specific
checkpointer backend directly. In-memory works and is used by default;
sqlite/redis are real dependencies (LangGraph ships both as separate
packages) intentionally left as TODOs rather than installed, so the base
scaffold doesn't carry deps most people won't need yet.
"""

from __future__ import annotations

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import InMemorySaver


def get_checkpointer(kind: str = "memory") -> BaseCheckpointSaver:
    if kind == "memory":
        return InMemorySaver()

    if kind == "sqlite":
        # pip install langgraph-checkpoint-sqlite
        # from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
        # return AsyncSqliteSaver.from_conn_string("checkpoints.db")
        raise NotImplementedError("sqlite checkpointer: add langgraph-checkpoint-sqlite and wire it in here")

    if kind == "redis":
        # pip install langgraph-checkpoint-redis
        # from langgraph.checkpoint.redis import AsyncRedisSaver
        # return AsyncRedisSaver(REDIS_URL)
        raise NotImplementedError("redis checkpointer: add langgraph-checkpoint-redis and wire it in here")

    raise ValueError(f"Unknown checkpointer kind: {kind}")
