import os
import json
import time
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

import pika
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, EmailStr

# NEW: LangGraph workflow
from app.workflow_graph import build_graph

# -----------------------------
# Config (LOCAL defaults)
# -----------------------------
RABBIT_URL = os.getenv("RABBIT_URL", "amqp://guest:guest@localhost:5672/")
TASKS_USER_QUEUE = os.getenv("TASKS_USER_QUEUE", "tasks.user")
TASKS_ORDER_QUEUE = os.getenv("TASKS_ORDER_QUEUE", "tasks.order")

RESULTS_QUEUE = os.getenv("RESULTS_QUEUE", "tasks.results")

RABBIT_CONNECT_RETRIES = int(os.getenv("RABBIT_CONNECT_RETRIES", "10"))
RABBIT_CONNECT_RETRY_DELAY_SEC = float(os.getenv("RABBIT_CONNECT_RETRY_DELAY_SEC", "1.0"))

TASK_RESULT_TIMEOUT_SEC = float(os.getenv("TASK_RESULT_TIMEOUT_SEC", "12.0"))
POLL_INTERVAL_SEC = float(os.getenv("POLL_INTERVAL_SEC", "0.25"))

app = FastAPI(title="Orchestrator Service", version="1.0.0")

# Build graph once (fast + clean)
GRAPH = build_graph()


# -----------------------------
# Request Schemas (MATCH user_service_v1/v2)
# -----------------------------
class CreateUserRequest(BaseModel):
    name: str = Field(..., min_length=1, examples=["Alex"])
    email: EmailStr = Field(..., examples=["alex@example.com"])
    delivery_address: str = Field(..., min_length=1, examples=["123 Street"])
    phone: Optional[str] = Field(None, examples=["1234567890"])


class UpdateAddressRequest(BaseModel):
    delivery_address: str = Field(..., min_length=1, examples=["456 New Street"])


class CreateOrderRequest(BaseModel):
    user_id: str = Field(..., min_length=1, examples=["u123"])
    items: list[dict] = Field(default_factory=list, examples=[[{"sku": "ABC123", "qty": 2}]])
    notes: Optional[str] = Field(None, examples=["Leave at the door"])


class ExecutePlanRequest(BaseModel):
    request_id: str = Field(..., min_length=1)
    actions: List[Dict[str, Any]] = Field(default_factory=list)


# -----------------------------
# RabbitMQ helpers
# -----------------------------
def _connect() -> pika.BlockingConnection:
    last_err: Optional[Exception] = None
    for _ in range(RABBIT_CONNECT_RETRIES):
        try:
            return pika.BlockingConnection(pika.URLParameters(RABBIT_URL))
        except Exception as e:
            last_err = e
            time.sleep(RABBIT_CONNECT_RETRY_DELAY_SEC)
    raise HTTPException(status_code=503, detail=f"RabbitMQ connection failed: {last_err}")


def _publish_to_queue(queue_name: str, message: Dict[str, Any]) -> None:
    payload = json.dumps(message).encode("utf-8")
    last_err: Optional[Exception] = None

    for _ in range(RABBIT_CONNECT_RETRIES):
        try:
            connection = pika.BlockingConnection(pika.URLParameters(RABBIT_URL))
            channel = connection.channel()

            channel.queue_declare(queue=queue_name, durable=True)
            channel.basic_publish(
                exchange="",
                routing_key=queue_name,
                body=payload,
                properties=pika.BasicProperties(
                    delivery_mode=2,
                    content_type="application/json",
                ),
            )
            connection.close()
            return

        except Exception as e:
            last_err = e
            time.sleep(RABBIT_CONNECT_RETRY_DELAY_SEC)

    raise HTTPException(
        status_code=503,
        detail=f"RabbitMQ publish failed for '{queue_name}': {last_err}",
    )


def _wait_for_result(request_id: str, task_id: str) -> Dict[str, Any]:
    connection = _connect()
    channel = connection.channel()
    channel.queue_declare(queue=RESULTS_QUEUE, durable=True)

    deadline = time.time() + TASK_RESULT_TIMEOUT_SEC

    try:
        while time.time() < deadline:
            method_frame, properties, body = channel.basic_get(queue=RESULTS_QUEUE, auto_ack=False)

            if method_frame is None:
                time.sleep(POLL_INTERVAL_SEC)
                continue

            try:
                msg = json.loads(body.decode("utf-8"))
            except Exception:
                channel.basic_ack(delivery_tag=method_frame.delivery_tag)
                continue

            if msg.get("request_id") == request_id and msg.get("task_id") == task_id:
                channel.basic_ack(delivery_tag=method_frame.delivery_tag)
                return msg

            channel.basic_nack(delivery_tag=method_frame.delivery_tag, requeue=True)
            time.sleep(0.05)

        raise HTTPException(
            status_code=504,
            detail=f"Timeout waiting for result (request_id={request_id}, task_id={task_id})",
        )
    finally:
        try:
            connection.close()
        except Exception:
            pass


# -----------------------------
# Health
# -----------------------------
@app.get("/health")
def health():
    return {"status": "ok", "service": "orchestrator"}


# -----------------------------
# Existing Orchestrator Endpoints (HTTP → TASK)
# -----------------------------
@app.post("/users", status_code=202)
def create_user(req: CreateUserRequest):
    # Keep existing behavior for Mode 1
    task = {
        "task_id": str(uuid.uuid4()),
        "trace_id": str(uuid.uuid4()),
        "type": "create_user",
        "payload": req.model_dump(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    _publish_to_queue(TASKS_USER_QUEUE, task)
    return {"accepted": True, "task_id": task["task_id"], "trace_id": task["trace_id"], "queue": TASKS_USER_QUEUE}


@app.put("/users/{user_id}/address", status_code=202)
def update_address(user_id: str, req: UpdateAddressRequest):
    task_payload = {"user_id": user_id, **req.model_dump()}
    task = {
        "task_id": str(uuid.uuid4()),
        "trace_id": str(uuid.uuid4()),
        "type": "update_address",
        "payload": task_payload,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    _publish_to_queue(TASKS_USER_QUEUE, task)
    return {"accepted": True, "task_id": task["task_id"], "trace_id": task["trace_id"], "queue": TASKS_USER_QUEUE}


@app.post("/orders", status_code=202)
def create_order(req: CreateOrderRequest):
    task = {
        "task_id": str(uuid.uuid4()),
        "trace_id": str(uuid.uuid4()),
        "type": "create_order",
        "payload": req.model_dump(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    _publish_to_queue(TASKS_ORDER_QUEUE, task)
    return {"accepted": True, "task_id": task["task_id"], "trace_id": task["trace_id"], "queue": TASKS_ORDER_QUEUE}


# -----------------------------
# Mode 2 endpoint (PLAN → LangGraph decide_task → TASKS → WAIT RESULTS)
# -----------------------------
@app.post("/execute-plan")
def execute_plan(req: ExecutePlanRequest):
    if not req.actions:
        raise HTTPException(status_code=400, detail="actions list is empty")

    context: Dict[str, Any] = {}
    results: List[Dict[str, Any]] = []

    for idx, action in enumerate(req.actions, start=1):
        action_type = (action or {}).get("type")
        if not action_type:
            raise HTTPException(status_code=400, detail=f"Action #{idx} missing 'type'")

        # Build state for LangGraph
        state: Dict[str, Any] = {
            "action": action_type,
            "request_id": req.request_id,
            "user_id": context.get("user_id"),
            "order_id": context.get("order_id"),
            "profile_complete": True,  # keep simple; you can compute later
            "task_payload": action,    # raw action dict from Gateway
        }

        # Run LangGraph node to decide queue + build task
        new_state = GRAPH.invoke(state)

        queue_name = new_state.get("task_queue")
        task = new_state.get("task")

        if not queue_name or not task:
            raise HTTPException(status_code=500, detail=f"Workflow did not produce task for action '{action_type}'")

        # Publish decided task
        _publish_to_queue(queue_name, task)

        # Wait for result
        task_id = task.get("task_id")
        if not task_id:
            raise HTTPException(status_code=500, detail="Task missing task_id")

        result = _wait_for_result(req.request_id, task_id)

        # Update context
        if result.get("ok") and isinstance(result.get("data"), dict):
            data = result["data"]
            if "user_id" in data:
                context["user_id"] = data["user_id"]
            if "order_id" in data:
                context["order_id"] = data["order_id"]

        results.append({
            "step": idx,
            "action": action_type,
            "task_id": task_id,
            "queue": queue_name,
            "ok": bool(result.get("ok")),
            "data": result.get("data"),
            "error": result.get("error"),
        })

        if not result.get("ok"):
            return {"request_id": req.request_id, "status": "FAILED", "context": context, "results": results}

    return {"request_id": req.request_id, "status": "SUCCESS", "context": context, "results": results}
