# orchestrator_service/app/workflow.py

from typing import TypedDict, Optional, Dict, Any, Literal


class OrchestrationState(TypedDict, total=False):
    """
    Shared state for orchestrator workflow.

    total=False means fields are optional and can be filled step-by-step.
    """

    # What the orchestrator is trying to do
    action: Literal["create_user", "update_address", "create_order", "checkout", "list_products"]

    # Correlation IDs (Mode 2)
    request_id: str
    task_id: str

    # Context (filled as we go)
    user_id: Optional[str]
    order_id: Optional[str]

    # Input coming from API (raw business payload)
    task_payload: Dict[str, Any]

    # Output decided by workflow
    task_queue: str
    task: Dict[str, Any]

    # Result returned by agent
    ok: bool
    data: Dict[str, Any]
    error: Optional[str]
