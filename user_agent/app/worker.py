import os, json, time
from typing import Any, Dict

import pika
import httpx

# ----------------------------
# LOCAL defaults (since you run locally, not Docker)
# ----------------------------
RABBIT_URL = os.getenv("RABBIT_URL", "amqp://guest:guest@localhost:5672/")

TASKS_USER_QUEUE = os.getenv("TASKS_USER_QUEUE", "tasks.user")
EVENTS_USER_QUEUE = os.getenv("EVENTS_USER_QUEUE", "events.user")
DEAD_USER_QUEUE = os.getenv("DEAD_USER_QUEUE", "dead.user")

# NEW: results queue for Mode 2 (orchestrator waits here)
RESULTS_QUEUE = os.getenv("RESULTS_QUEUE", "tasks.results")

USER_V1_URL = os.getenv("USER_V1_URL", "http://127.0.0.1:8002")
USER_V2_URL = os.getenv("USER_V2_URL", "http://127.0.0.1:8003")

USER_CREATE_PATH = os.getenv("USER_CREATE_PATH", "/users")
USER_ADDRESS_PATH = os.getenv("USER_ADDRESS_PATH", "/users/{user_id}/address")

PREFETCH = int(os.getenv("PREFETCH", "1"))
RETRY_DELAY_SEC = float(os.getenv("RETRY_DELAY_SEC", "1.0"))
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))


def connect_rabbit() -> pika.BlockingConnection:
    return pika.BlockingConnection(pika.URLParameters(RABBIT_URL))


def declare(channel, queue: str):
    channel.queue_declare(queue=queue, durable=True)


def publish_json(channel, queue: str, msg: Dict[str, Any]):
    declare(channel, queue)
    channel.basic_publish(
        exchange="",
        routing_key=queue,
        body=json.dumps(msg).encode("utf-8"),
        properties=pika.BasicProperties(
            delivery_mode=2,  # persistent
            content_type="application/json"
        ),
    )


def choose_user_base(task: Dict[str, Any]) -> str:
    # Keep your current behavior: force v1 while debugging
    return USER_V1_URL


def handle_task_http(base_url: str, task_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    with httpx.Client(timeout=10.0) as client:
        if task_type == "create_user":
            r = client.post(f"{base_url}{USER_CREATE_PATH}", json=payload)
            r.raise_for_status()
            return {"event_type": "user_created", "result": r.json()}

        if task_type == "update_address":
            user_id = payload.get("user_id")
            if not user_id:
                raise ValueError("update_address payload missing 'user_id'")

            body = dict(payload)
            body.pop("user_id", None)

            r = client.put(
                f"{base_url}{USER_ADDRESS_PATH.format(user_id=user_id)}",
                json=body
            )
            r.raise_for_status()
            return {"event_type": "address_updated", "result": r.json()}

        raise ValueError(f"Unknown task type: {task_type}")


def main():
    while True:
        try:
            print(f"[UserAgent] Connecting to RabbitMQ: {RABBIT_URL}")
            connection = connect_rabbit()
            channel = connection.channel()

            declare(channel, TASKS_USER_QUEUE)
            declare(channel, RESULTS_QUEUE)  # NEW (ensure exists)
            channel.basic_qos(prefetch_count=PREFETCH)

            print(f"[UserAgent] Listening: {TASKS_USER_QUEUE}")
            print(f"[UserAgent] Results: {RESULTS_QUEUE}")
            print(f"[UserAgent] Events: {EVENTS_USER_QUEUE} | Dead: {DEAD_USER_QUEUE}")
            print(f"[UserAgent] Tools: V1={USER_V1_URL} | V2={USER_V2_URL}")

            def callback(ch, method, properties, body: bytes):
                task = json.loads(body.decode("utf-8"))
                task_type = task.get("type")
                payload = task.get("payload", {})

                task_id = task.get("task_id")
                trace_id = task.get("trace_id")

                # NEW: Mode 2 correlation
                request_id = task.get("request_id")

                retries = int(task.get("retries", 0))
                base_url = choose_user_base(task)

                print(
                    f"\n[UserAgent] task={task_type} id={task_id} request_id={request_id} "
                    f"trace={trace_id} retries={retries}"
                )

                try:
                    out = handle_task_http(base_url, task_type, payload)

                    # Existing event publish (keep for your current flows)
                    event = {
                        "type": out["event_type"],
                        "task_id": task_id,
                        "trace_id": trace_id,
                        "timestamp": time.time(),
                        "target": task.get("target", "v1"),
                        "result": out["result"],
                    }
                    publish_json(ch, EVENTS_USER_QUEUE, event)

                    # NEW: publish result for orchestrator Mode 2
                    # Orchestrator expects: request_id + task_id
                    result_msg = {
                        "request_id": request_id,
                        "task_id": task_id,
                        "ok": True,
                        "data": {},
                        "error": None,
                    }

                    # Normalize common fields so orchestrator can update context
                    # Your user service response may return "id" or "user_id"
                    resp = out["result"] if isinstance(out["result"], dict) else {}
                    user_id = resp.get("id") or resp.get("user_id")
                    if user_id:
                        result_msg["data"]["user_id"] = user_id
                    result_msg["data"]["raw"] = resp

                    publish_json(ch, RESULTS_QUEUE, result_msg)

                    print(f"[UserAgent] ✅ Done. Published {event['type']} + result(ok=True)")
                    ch.basic_ack(delivery_tag=method.delivery_tag)

                except Exception as e:
                    print(f"[UserAgent] ❌ Error: {e}")

                    # Publish failure result for orchestrator Mode 2 (so it can stop)
                    fail_msg = {
                        "request_id": request_id,
                        "task_id": task_id,
                        "ok": False,
                        "data": {},
                        "error": str(e),
                    }
                    publish_json(ch, RESULTS_QUEUE, fail_msg)

                    retries += 1
                    task["retries"] = retries
                    task["error"] = str(e)

                    if retries >= MAX_RETRIES:
                        publish_json(ch, DEAD_USER_QUEUE, task)
                        print(f"[UserAgent] 🪦 Sent to dead queue after {retries} tries")
                        ch.basic_ack(delivery_tag=method.delivery_tag)
                    else:
                        time.sleep(RETRY_DELAY_SEC)
                        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

            channel.basic_consume(queue=TASKS_USER_QUEUE, on_message_callback=callback)
            channel.start_consuming()

        except Exception as e:
            print(f"[UserAgent] Connection error: {e}. Retrying in {RETRY_DELAY_SEC}s...")
            time.sleep(RETRY_DELAY_SEC)


if __name__ == "__main__":
    main()
