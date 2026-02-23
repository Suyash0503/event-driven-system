import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional


def _now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_trace_id() -> str:
    return str(uuid.uuid4())


def build_task(
    task_type: str,
    payload: Dict[str, Any],
    trace_id: Optional[str] = None,
    request_id: Optional[str] = None,  # NEW (Mode 2)
) -> Dict[str, Any]:
    """
    Task envelope used by agents.
    - request_id groups tasks for a single NL command (Mode 2)
    - trace_id is for tracing/logging
    """
    return {
        "task_id": str(uuid.uuid4()),
        "request_id": request_id,  # NEW
        "trace_id": trace_id or new_trace_id(),
        "type": task_type,
        "payload": payload,
        "timestamp": _now_utc_iso(),
        "status": "queued",
        "source": "orchestrator_service",
    }


# -----------------------------
# User tasks (MATCH user_service)
# -----------------------------
def task_create_user(
    name: str,
    email: str,
    delivery_address: str,
    trace_id: Optional[str] = None,
    request_id: Optional[str] = None,  # NEW
) -> Dict[str, Any]:
    payload = {
        "name": name,
        "email": email,
        "delivery_address": delivery_address,
    }
    return build_task("create_user", payload, trace_id=trace_id, request_id=request_id)


def task_update_address(
    user_id: str,
    delivery_address: str,
    trace_id: Optional[str] = None,
    request_id: Optional[str] = None,  # NEW
) -> Dict[str, Any]:
    payload = {
        "user_id": user_id,
        "delivery_address": delivery_address,
    }
    return build_task("update_address", payload, trace_id=trace_id, request_id=request_id)


# -----------------------------
# Order tasks
# -----------------------------
def task_create_order(
    user_id: str,
    items: list,
    notes: Optional[str] = None,
    trace_id: Optional[str] = None,
    request_id: Optional[str] = None,  # NEW
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "user_id": user_id,
        "items": items,
    }
    if notes is not None:
        payload["notes"] = notes

    return build_task("create_order", payload, trace_id=trace_id, request_id=request_id)


def task_checkout_order(
    order_id: str,
    trace_id: Optional[str] = None,
    request_id: Optional[str] = None,  # NEW
) -> Dict[str, Any]:
    """
    NEW: checkout task (Mode 2).
    Agent should call order_service checkout endpoint and return status.
    """
    payload = {"order_id": order_id}
    return build_task("checkout", payload, trace_id=trace_id, request_id=request_id)
