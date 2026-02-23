import os
from app.workflow import OrchestrationState
from app.tasks import (
    task_create_user,
    task_update_address,
    task_create_order,
    task_checkout_order,   # NEW
)

# Keep queues configurable (matches your main.py env defaults)
TASKS_USER_QUEUE = os.getenv("TASKS_USER_QUEUE", "tasks.user")
TASKS_ORDER_QUEUE = os.getenv("TASKS_ORDER_QUEUE", "tasks.order")


def decide_task(state: OrchestrationState) -> OrchestrationState:
    """
    LangGraph node: decides which queue to use and builds the task message.

    Expects state to contain:
      - state["action"]
      - state["task_payload"] (dict)
      - state["request_id"] (optional but used in Mode 2)
      - state["user_id"] / state["order_id"] as context (optional)
    """
    action = state["action"]
    payload = state.get("task_payload", {}) or {}

    request_id = state.get("request_id")  # Mode 2 correlation id

    if action == "create_user":
        # Gateway may send "address" instead of "delivery_address"
        delivery_address = payload.get("delivery_address") or payload.get("address")

        if not payload.get("name") or not payload.get("email") or not delivery_address:
            raise Exception("create_user requires: name, email, address/delivery_address")

        state["task"] = task_create_user(
            payload["name"],
            payload["email"],
            delivery_address,
            request_id=request_id,
        )
        state["task_queue"] = TASKS_USER_QUEUE

    elif action == "update_address":
        # Resolve user_id from payload or context
        user_id = payload.get("user_id") or state.get("user_id")
        delivery_address = payload.get("delivery_address") or payload.get("address")

        if not user_id:
            raise Exception("update_address requires user_id (or user_id in context)")
        if not delivery_address:
            raise Exception("update_address requires: address/delivery_address")

        state["task"] = task_update_address(
            user_id,
            delivery_address,
            request_id=request_id,
        )
        state["task_queue"] = TASKS_USER_QUEUE

    elif action == "create_order":
        # Optional strictness check
        if state.get("profile_complete") is False:
            raise Exception("User profile incomplete. Cannot place order.")

        user_id = payload.get("user_id") or state.get("user_id")
        if not user_id:
            raise Exception("create_order requires user_id (or user_id in context)")

        # ✅ FIX: support items[] OR product_id+quantity OR item+quantity
        items = payload.get("items")

        # If items missing/empty, try product_id + quantity
        if not items:
            product_id = payload.get("product_id")
            qty = payload.get("quantity", 1)
            if product_id:
                items = [{"sku": product_id, "qty": int(qty)}]

        # If still empty, try item + quantity
        if not items:
            item = payload.get("item")
            qty = payload.get("quantity", 1)
            if item:
                items = [{"sku": item, "qty": int(qty)}]

        if not items:
            raise Exception("create_order requires items[] OR product_id+quantity OR item+quantity")

        state["task"] = task_create_order(
            user_id,
            items,
            payload.get("notes"),
            request_id=request_id,
        )
        state["task_queue"] = TASKS_ORDER_QUEUE

    elif action == "checkout":
        order_id = payload.get("order_id") or state.get("order_id")
        if not order_id:
            raise Exception("checkout requires order_id (or order_id in context)")

        state["task"] = task_checkout_order(
            order_id,
            request_id=request_id,
        )
        state["task_queue"] = TASKS_ORDER_QUEUE

    elif action == "list_products":
        # If you don't have product_service yet, route this to order agent for now
        state["task"] = {
            "task_id": "noop",
            "request_id": request_id,
            "trace_id": "noop",
            "type": "list_products",
            "payload": {},
            "timestamp": "",
            "status": "queued",
            "source": "orchestrator_service",
        }
        state["task_queue"] = TASKS_ORDER_QUEUE

    else:
        raise Exception(f"Unknown action: {action}")

    return state
