"""The orchestrator's routing rules.

The planner picks which agents run; the orchestrator's model picks when
(skills/orchestrator/skill.md). `broken_rules` only rejects a route that would
break the run — it never chooses one. Every message names the fix, because the
model reads it on the retry.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from dataclasses import dataclass
from typing import Any

from langgraph.graph import END

from agents.graph.edges import NODES, OUTPUT_VALIDATOR, STAGE_AGENTS
from agents.graph.states import State, is_finished
from agents.nodes.planner.node import MAX_PLANS
from agents.nodes.stage_agent import MAX_RUNS

# nodes that never share a step with another
_ALONE = frozenset({"planner", "review", "execution", OUTPUT_VALIDATOR, END})


@dataclass(frozen=True)
class _Run:
    """The facts every rule reads, computed once from the state."""

    planned: frozenset[str]
    finished: frozenset[str]
    runs: dict[str, int]
    open_needs: tuple[dict[str, Any], ...]
    reviewed: str | None
    validated: dict[str, Any] | None

    @classmethod
    def of(cls, state: State) -> _Run:
        results = state.get("results") or {}
        return cls(
            planned=frozenset(s["agent"] for s in state.get("plan") or []),
            finished=frozenset(a for a in results if is_finished(results, a)),
            runs=dict(state.get("runs") or {}),
            open_needs=tuple(n for n in state.get("needs") or [] if n["status"] == "open"),
            reviewed=(state.get("review") or {}).get("action"),
            validated=results[OUTPUT_VALIDATOR] if is_finished(results, OUTPUT_VALIDATOR) else None,
        )

    @property
    def open_ids(self) -> list[str]:
        return [n["id"] for n in self.open_needs]

    @property
    def unfinished(self) -> list[str]:
        """Planned stage agents with no result yet (execution is not a stage agent)."""
        return [a for a in STAGE_AGENTS if a in self.planned and a not in self.finished]

    def waiting_on(self, agent: str) -> list[str]:
        return [n["id"] for n in self.open_needs if n["from_agent"] == agent]

    def is_asked(self, agent: str) -> bool:
        return any(n["ask"] == agent for n in self.open_needs)


Rule = Callable[[_Run, list[str]], Iterator[str]]


# ── rules: each yields what is wrong, nothing when the route is fine ─────────

def _alone(run: _Run, route: list[str]) -> Iterator[str]:
    if len(route) > 1 and (alone := sorted(set(route) & _ALONE)):
        yield f"{alone} must run alone"


def _after_review(run: _Run, route: list[str]) -> Iterator[str]:
    if run.reviewed and route != [END]:
        yield f"the run was already reviewed ({run.reviewed}) — only __end__ can follow"


def _stage_agents(run: _Run, route: list[str]) -> Iterator[str]:
    for agent in (a for a in STAGE_AGENTS if a in route):
        if agent not in run.planned and not run.is_asked(agent):
            yield f"{agent} is not in the plan and nobody asked it anything"
        if waiting := run.waiting_on(agent):
            yield f"{agent} is waiting on {waiting} — answer or fail those first"
        if run.runs.get(agent, 0) >= MAX_RUNS:
            yield f"{agent} already ran {MAX_RUNS} times — fail what it was asked instead"


def _fetch(run: _Run, route: list[str]) -> Iterator[str]:
    # fetch closes every request it is given (done or failed), so it needs no run cap
    if "fetch" in route and not run.is_asked("execution"):
        yield "fetch needs an open request to execution"


def _all_settled(run: _Run, node: str) -> Iterator[str]:
    """Execution and review both need every stage agent done and no request open."""
    if run.unfinished:
        yield f"{node} comes once every stage agent has finished; still to run: {run.unfinished}"
    if run.open_needs:
        yield f"{node} must wait until every request is answered or failed: {run.open_ids}"


def _execution(run: _Run, route: list[str]) -> Iterator[str]:
    if "execution" not in route:
        return
    if "execution" not in run.planned:
        yield "execution is not in the plan"
    if "execution" in run.finished:
        yield "execution already ran"
    yield from _all_settled(run, "execution")


def _output_validator(run: _Run, route: list[str]) -> Iterator[str]:
    if OUTPUT_VALIDATOR not in route:
        return
    if "execution" not in run.finished:
        yield f"{OUTPUT_VALIDATOR} checks execution's package — run execution first"
    if OUTPUT_VALIDATOR in run.finished:
        yield f"{OUTPUT_VALIDATOR} already checked this package"


def _replan(run: _Run, route: list[str]) -> Iterator[str]:
    if "planner" not in route:
        return
    if not run.validated or run.validated.get("valid") is not False:
        yield f"the planner already ran — it plans again only after {OUTPUT_VALIDATOR} finds issues"
    elif run.runs.get("planner", 0) >= MAX_PLANS:
        yield f"the planner already planned {MAX_PLANS} times — route review"


def _review(run: _Run, route: list[str]) -> Iterator[str]:
    if "review" not in route:
        return
    if not run.planned:
        yield "an empty plan has nothing to review — route __end__"
        return
    if "execution" in run.planned and "execution" not in run.finished:
        yield "review is the last step — run execution first"
    elif "execution" in run.planned and OUTPUT_VALIDATOR not in run.finished:
        yield f"review comes after {OUTPUT_VALIDATOR} — route it first"
    yield from _all_settled(run, "review")


def _end(run: _Run, route: list[str]) -> Iterator[str]:
    if route == [END] and run.planned and not run.reviewed:
        yield "the run can't end before review — finish every agent, execution included, then route review"


_RULES: tuple[Rule, ...] = (
    _alone, _after_review, _stage_agents, _fetch, _execution, _output_validator, _replan, _review, _end,
)


def broken_rules(state: State, route: list[str]) -> list[str]:
    """Why `route` can't run now — empty when it can."""
    if not route:
        return ["route is empty"]
    if unknown := [n for n in route if n not in NODES]:
        return [f"unknown nodes {unknown}; use {list(NODES)}"]

    run = _Run.of(state)
    # until the planner has run, nothing else is meaningful
    if "planner" not in run.finished:
        return [] if route == ["planner"] else ['the planner has not run yet — route ["planner"] alone']

    return [error for rule in _RULES for error in rule(run, route)]
