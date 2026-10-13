from datetime import UTC, datetime
from typing import Annotated, Any, Literal, NotRequired, TypedDict
import operator

Stage = Literal["planning", "validation", "compliance", "payroll", "execution"]


# one step of the planner's plan: which agent runs, and what to focus on
class PlanStep(TypedDict):
    agent: str                  # a graph node name, e.g. "validation"
    task: str


# one row of the case timeline the UI shows
class StepRecord(TypedDict):
    stage: Stage
    agent: str
    title: str
    source: str                 # system the step read from, e.g. "MCP · get_service_order"
    at: str                     # ISO-8601 UTC
    result: NotRequired[str]
    evidence: NotRequired[dict[str, Any]]


# an issue an agent found, shown to the reviewer at the end of the run
class Flag(TypedDict):
    flag_id: str
    type: str                   # e.g. "duplicateSO", "complianceTiming", "netPayMismatch"
    stage: Stage
    title: str
    detail: dict[str, Any]
    recommendation: NotRequired[str | None]  # what Execution does about it if the run is approved; null for a data problem
    resolved: bool              # true only once merged into another flag
    decisions: list[dict[str, Any]]  # what happened to it, e.g. {"action": "merged", "into": ...}


# the reviewer's one decision on the whole run, before execution
class Review(TypedDict):
    action: Literal["approve", "reject"]
    reason: NotRequired[str]    # required for reject
    flags_seen: NotRequired[list[str]]  # the flag ids in front of the reviewer, for the audit trail


# what an agent asks another agent for, through the orchestrator
class Need(TypedDict):
    id: str                     # "n1", "n2", … given by the orchestrator
    from_agent: str             # who asked, e.g. "validation"
    ask: str                    # who should answer, e.g. "execution" or "compliance"
    request: str                # plain text, e.g. "Employee record for EMP-2003"
    args: dict[str, Any]        # facts that help answer it
    for_need: str | None        # the need this one serves, when needs chain
    status: Literal["open", "done", "failed"]
    answer: Any                 # filled in by whoever answered
    error: str | None           # why it failed


# one finished call of a graph node, for the console's per-agent figures
class NodeTiming(TypedDict):
    agent: str                  # the graph node name, e.g. "payroll-calculation"
    started_at: str             # ISO-8601 UTC
    finished_at: str            # ISO-8601 UTC


def merge_flags(current: list[Flag], new: list[Flag]) -> list[Flag]:
    """Each agent adds its own flags; the orchestrator sends back an updated
    copy of one it merged. A flag with a known flag_id replaces it in place."""
    by_id = {f["flag_id"]: f for f in current}
    by_id.update({f["flag_id"]: f for f in new})
    return list(by_id.values())


def merge_needs(current: list[Need], new: list[Need]) -> list[Need]:
    """Same as merge_flags: a need with a known id is replaced in place."""
    by_id = {n["id"]: n for n in current}
    by_id.update({n["id"]: n for n in new})
    return list(by_id.values())


def is_finished(results: dict[str, Any], node: str) -> bool:
    """A node has finished once it has a result — unless a re-plan marked that
    result `rerun`. The marked result stays, so the node sees what it did before."""
    result = results.get(node)
    return result is not None and not result.get("rerun")


#generic for all the agents
class State(TypedDict):
    schema_version: int
    run_id: str                 # LangGraph thread_id stays in config
    service_order_id: NotRequired[str]
    service_order: NotRequired[dict[str, Any]]  # the record fetched by id before the run starts
    query: NotRequired[str]     # fallback: the order described as text, when no id is given
    status: Literal["running", "needs_review", "done", "rejected", "failed"]
    plan: NotRequired[list[PlanStep]]  # the planner's plan; the orchestrator runs it in order
    flagged: bool               # an agent raised a flag (shown at review and in the result)
    review: NotRequired[Review]  # the reviewer's decision, once given; execution needs "approve"
    priority: NotRequired[Literal["high", "medium", "low"]]  # planner's decision, raised a level once any flag is raised
    confidence: NotRequired[int]  # 0-100: the lowest stage confidence, once a stage has reported
    mcp_results: NotRequired[list[dict[str, Any]]]  # MCP tool calls, for later agents
    results: Annotated[dict[str, dict[str, Any]], operator.or_]  # agent name -> its output (planner: its plan + priority); "rerun": true = run again after a re-plan
    steps: Annotated[list[StepRecord], operator.add]
    flags: Annotated[list[Flag], merge_flags]
    needs: Annotated[list[Need], merge_needs]  # agents' requests to each other, routed by the orchestrator
    runs: Annotated[dict[str, int], operator.or_]  # agent name -> times it has run (loop guard)
    timings: NotRequired[Annotated[list[NodeTiming], operator.add]]  # every finished node call; a failed attempt adds none
    worker_results: NotRequired[Annotated[dict[str, list[dict[str, Any]]], operator.or_]]  # agent name -> its worker tasks and their results
    route: NotRequired[list[str]]  # the orchestrator model's choice of next hops, checked by nodes/orchestrator/route_rules.py
    summary: NotRequired[str]   # the orchestrator model's latest summary of the run, for the reviewer
    pipeline: NotRequired[list[dict[str, Any]]]  # the console's stages, in order; see graph/pipeline.py
    final_output: NotRequired[dict[str, Any]]
    error: NotRequired[str]


def step_record(stage: Stage, agent: str, title: str, source: str, **extra: Any) -> StepRecord:
    return {
        "stage": stage,
        "agent": agent,
        "title": title,
        "source": source,
        "at": datetime.now(UTC).isoformat(),
        **extra,
    }
