"""Dedupe by task hash, so the same message replayed off a queue (a normal
at-least-once delivery scenario) doesn't run the graph twice. In-memory set
for now — real version: Redis SETNX with a TTL, so it survives restarts and
works across multiple worker processes.
"""

from __future__ import annotations

import hashlib

_seen: set[str] = set()


def idempotency_key(task: str) -> str:
    return hashlib.sha256(task.encode()).hexdigest()


def already_processed(key: str) -> bool:
    return key in _seen


def mark_processed(key: str) -> None:
    _seen.add(key)
