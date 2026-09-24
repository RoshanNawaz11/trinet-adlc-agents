"""Named example queries so the CLI does not need a pasted paragraph."""

from __future__ import annotations

SAMPLES: dict[str, str] = {
    "checkout": (
        "Ticket #420: Customers report the checkout page returns a 500 error "
        "when applying a discount code larger than 20%. Started after yesterday's "
        "deploy of the pricing-service. Affects roughly 15% of checkout attempts. "
        "Support has received 8 complaints in the last hour. Please summarize this "
        "ticket and classify its priority."
    ),
    "priya": (
        "HR request from Priya Sharma: she asked for a copy of her latest payslip "
        "and confirmation of her current department, job title, location, and "
        "employment status. Please look her up, summarize the request, and "
        "classify its priority."
    ),
}


def sample_query(name: str) -> str:
    key = name.strip().lower()
    try:
        return SAMPLES[key]
    except KeyError:
        known = ", ".join(sorted(SAMPLES))
        raise KeyError(f"unknown sample {name!r}; known: {known}") from None


def format_samples() -> str:
    blocks = [f"{name}:\n  {text}\n" for name, text in sorted(SAMPLES.items())]
    return "\n".join(blocks)


def resolve_query(*, query: str | None, sample: str | None, resume: bool) -> str:
    """Pick the query string the worker should run.

    `--resume` may omit a query. `--sample` and a positional query cannot both
    be set. Raises ValueError with a CLI-ready message when the combo is invalid.
    """
    if resume:
        return query or ""
    if sample:
        if query:
            raise ValueError("pass either a query or --sample, not both")
        return sample_query(sample)
    if not query:
        raise ValueError("query is required unless --resume, --sample, or --list-samples")
    return query
