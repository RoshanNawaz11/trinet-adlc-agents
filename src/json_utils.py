"""Best-effort JSON extraction from a model response.

Even with an explicit "respond with ONLY JSON" instruction, models
occasionally wrap output in markdown fences or add a stray sentence. This
pulls out the first top-level `{...}` or `[...]` block and parses that,
rather than assuming `response.strip()` is valid JSON outright.
"""

from __future__ import annotations

import json
import re

_JSON_BLOCK = re.compile(r"[\{\[].*[\}\]]", re.DOTALL)


class JSONParseError(ValueError):
    pass


def extract_json(text: str) -> object:
    match = _JSON_BLOCK.search(text)
    if not match:
        raise JSONParseError(f"No JSON object/array found in model output: {text!r}")
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError as exc:
        raise JSONParseError(f"Model output looked like JSON but didn't parse: {exc}") from exc
