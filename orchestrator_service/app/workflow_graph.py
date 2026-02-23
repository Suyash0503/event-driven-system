# orchestrator_service/app/workflow_graph.py

from langgraph.graph import StateGraph, END

from app.workflow import OrchestrationState
from app.workflow_nodes import decide_task


def build_graph():
    """
    Builds and returns a compiled LangGraph workflow.

    Flow:
      START -> decide_task -> END

    decide_task() fills:
      - state["task_queue"]
      - state["task"]
    """
    graph = StateGraph(OrchestrationState)

    # Node(s)
    graph.add_node("decide_task", decide_task)

    # Entry point
    graph.set_entry_point("decide_task")

    # End
    graph.add_edge("decide_task", END)

    return graph.compile()
