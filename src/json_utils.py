"""Best-effort JSON extraction from a model response.

Even with an explicit "respond with ONLY JSON" instruction, models
occasionally wrap output in markdown fences or add a stray sentence. This
pulls out the first top-level `{...}` or `[...]` block and parses that,
rather than assuming `response.strip()` is valid JSON outright.
"""

from __future__ import annotations

import json


class JSONParseError(ValueError):
    pass


def _json_values(text: str):
    """Each top-level JSON value in `text`, in order.

    `raw_decode` stops at the end of a value, so a later object or a trailing
    sentence does not fail with Extra data.
    """
    decoder = json.JSONDecoder()
    index = 0
    while index < len(text):
        start = next((i for i in range(index, len(text)) if text[i] in "{["), None)
        if start is None:
            return
        try:
            value, end = decoder.raw_decode(text, start)
        except json.JSONDecodeError:
            index = start + 1
            continue
        yield value
        index = end


def has_json_object(text: str) -> bool:
    """Whether `text` holds at least one JSON object — the shape every caller expects."""
    return any(isinstance(value, dict) for value in _json_values(text))


def extract_json(text: str, *, key: str | None = None) -> object:
    """Parse a JSON value out of a model response.

    Without `key`, this is the first value. With `key`, it is the last object
    that contains that key, so a quoted example earlier in the answer (an
    empty `[]`, for instance) does not hide the real object.
    """
    found = None
    for value in _json_values(text):
        if key is None:
            return value
        if isinstance(value, dict) and key in value:
            found = value
    if found is not None:
        return found
    raise JSONParseError(f"No JSON object/array found in model output: {text!r}")
