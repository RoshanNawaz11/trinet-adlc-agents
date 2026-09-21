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


def extract_json(text: str) -> object:
    """Parse the first top-level JSON value in `text`.

    `JSONDecoder.raw_decode` stops at the end of that value, so a second
    object or a trailing sentence does not fail with Extra data. The greedy
    `{...}` regex used to swallow everything from the first brace to the
    last, which is invalid JSON when the model emits two objects.
    """
    decoder = json.JSONDecoder()
    for index, char in enumerate(text):
        if char not in "{[":
            continue
        try:
            value, _ = decoder.raw_decode(text, index)
            return value
        except json.JSONDecodeError:
            continue
    raise JSONParseError(f"No JSON object/array found in model output: {text!r}")
