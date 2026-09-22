import logging
import os

from langwatch.telemetry.context import get_current_trace
from langwatch.telemetry.tracing import trace as _lw_trace


logger = logging.getLogger(__name__)


def maybe_trace(name: str):
    if os.getenv("LANGWATCH_DISABLED", "false").lower() == "true":
        return lambda fn: fn  # no-op decorator — runs fn() untouched
    return _lw_trace(name=name)


def attach_metadata(**fields):
    try:
        get_current_trace().update(metadata=fields)
    except Exception:
        logger.exception("Failed to attach LangWatch metadata")