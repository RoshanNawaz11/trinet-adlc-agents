from langgraph.graph import END, START, StateGraph

from agents.graph.edges import route_after_planner
from agents.graph.interrupts import INTERRUPT_BEFORE
from agents.graph.states import State
from agents.nodes.expert.node import expert_node
from agents.nodes.orchestrator.node import orchestrator_node
from agents.nodes.planner.node import planner_node
from agents.nodes.worker.node import worker_node
from agents.runtime.checkpointer import get_checkpointer

def aggregate_node(state: State) -> dict:
    final_output = {r["step_id"]: r["output"] for r in state.get("step_results", [])}
    errors = [r["error"] for r in state.get("step_results", []) if r.get("error")]
    escalations = [
        r["escalation"] for r in state.get("step_results", []) if r.get("escalation")
    ]
    if errors:
        return {
            "final_output": final_output,
            "status": "failed",
            "error": "; ".join(errors),
        }
    return {
        "final_output": final_output,
        "status": "needs_review" if escalations else "done",
        "flagged": bool(escalations),
    }


def build_graph(checkpointer_kind: str = "memory") -> State:
    graph = StateGraph(State)

    graph.add_node("orchestrator", orchestrator_node)
    graph.add_node("planner", planner_node)
    graph.add_node("expert", expert_node)
    graph.add_node("worker", worker_node)
    graph.add_node("aggregate", aggregate_node)

    graph.add_edge(START, "orchestrator")
    graph.add_edge("orchestrator", "planner")
    graph.add_conditional_edges("planner", route_after_planner, ["expert", "worker"])
    graph.add_edge("expert", "aggregate")
    graph.add_edge("worker", "aggregate")
    graph.add_edge("aggregate", END)

    return graph.compile(
        checkpointer=get_checkpointer(checkpointer_kind),
        interrupt_before=INTERRUPT_BEFORE,
    )
