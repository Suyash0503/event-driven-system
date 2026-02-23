import os
import json
import time
from typing import Any, Dict, Optional

import pika
import httpx

# LOCAL defaults (not Docker)
RABBIT_URL = os.getenv("RABBIT_URL", "amqp://guest:guest@localhost:5672/")

TASKS_ORDER_QUEUE = os.getenv("TASKS_ORDER_QUEUE", "tasks.order")
EVENTS_ORDER_QUEUE = os.getenv("EVENTS_ORDER_QUEUE", "events.order")
DEAD_ORDER_QUEUE = os.getenv("DEAD_ORDER_QUEUE", "dead.order")

# NEW: results queue for Mode 2
RESULTS_QUEUE = os.getenv("RESULTS_QUEUE", "tasks.results")

ORDER_URL = os.getenv("ORDER_URL", "http://127.0.0.1:8001")
USER_V1_URL = os.getenv("USER_V1_URL", "http://127.0.0.1:8002")
USER_V2_URL = os.getenv("USER_V2_URL", "http://127.0.0.1:8003")

PREFETCH = int(os.getenv("PREFETCH", "1"))
RETRY_DELAY_SEC = float(os.getenv("RETRY_DELAY_SEC", "1.0"))
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))

# endpoints
ORDER_CREATE_PATH = os.getenv("ORDER_CREATE_PATH", "/orders")
ORDER_CHECKOUT_PATH = os.getenv("ORDER_CHECKOUT_PATH", "/orders/{order_id}/checkout")
USER_GET_PATH = os.getenv("USER_GET_PATH", "/users/{user_id}")


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
        properties=pika.BasicProperties(delivery_mode=2, content_type="application/json"),
    )


async def fetch_user(user_id: str) -> Dict[str, Any]:
    """
    Fetch user from v2 then v1 (demo-friendly). Returns user JSON.
    Raises if not found.
    """
    async with httpx.AsyncClient(timeout=8.0) as client:
        last_err: Optional[str] = None
        for base in (USER_V2_URL, USER_V1_URL):
            url = f"{base}{USER_GET_PATH.format(user_id=user_id)}"
            try:
                r = await client.get(url)
                if r.status_code == 200:
                    return r.json()
                last_err = f"{base} -> {r.status_code} {r.text}"
            except Exception as e:
                last_err = repr(e)
        raise ValueError(f"User not found or user service error: {last_err}")


def items_to_single_item(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Your order_service schema is single-item: item + quantity.
    We convert from items[] if present, otherwise accept item/quantity if already provided.
    """
    # already in correct shape
    if payload.get("item") and payload.get("quantity"):
        return {"item": payload["item"], "quantity": payload["quantity"]}

    items = payload.get("items") or []
    if not items:
        # fallback to product_id/quantity if present
        product_id = payload.get("product_id")
        qty = payload.get("quantity", 1)
        if product_id:
            return {"item": product_id, "quantity": int(qty)}
        raise ValueError("No items provided. Need items[] or item+quantity or product_id.")

    first = items[0]
    sku = first.get("sku")
    qty = first.get("qty", 1)
    if not sku:
        raise ValueError("First item missing 'sku'")
    return {"item": sku, "quantity": int(qty)}


async def create_order(order_body: Dict[str, Any]) -> Dict[str, Any]:
    async with httpx.AsyncClient(timeout=12.0) as client:
        url = f"{ORDER_URL}{ORDER_CREATE_PATH}"
        r = await client.post(url, json=order_body)
        r.raise_for_status()
        return r.json()


async def checkout_order(order_id: str) -> Dict[str, Any]:
    async with httpx.AsyncClient(timeout=12.0) as client:
        url = f"{ORDER_URL}{ORDER_CHECKOUT_PATH.format(order_id=order_id)}"
        r = await client.post(url)
        r.raise_for_status()
        return r.json()


def main():
    while True:
        try:
            print(f"[OrderAgent] Connecting to RabbitMQ: {RABBIT_URL}")
            connection = connect_rabbit()
            channel = connection.channel()

            declare(channel, TASKS_ORDER_QUEUE)
            declare(channel, RESULTS_QUEUE)
            channel.basic_qos(prefetch_count=PREFETCH)

            print(f"[OrderAgent] Listening: {TASKS_ORDER_QUEUE}")
            print(f"[OrderAgent] Results: {RESULTS_QUEUE}")
            print(f"[OrderAgent] Events: {EVENTS_ORDER_QUEUE} | Dead: {DEAD_ORDER_QUEUE}")
            print(f"[OrderAgent] Tool: ORDER={ORDER_URL} | USER_V1={USER_V1_URL} | USER_V2={USER_V2_URL}")

            def callback(ch, method, properties, body: bytes):
                task = json.loads(body.decode("utf-8"))
                task_type = task.get("type")
                payload = task.get("payload", {})
                task_id = task.get("task_id")
                trace_id = task.get("trace_id")
                request_id = task.get("request_id")
                retries = int(task.get("retries", 0))

                print(f"\n[OrderAgent] task={task_type} id={task_id} request_id={request_id} trace={trace_id} retries={retries}")

                try:
                    import asyncio

                    if task_type == "create_order":
                        user_id = payload.get("user_id")
                        if not user_id:
                            raise ValueError("create_order payload missing 'user_id'")

                        user = asyncio.run(fetch_user(user_id))
                        email = user.get("email")
                        delivery_address = user.get("delivery_address")

                        if not email or not delivery_address:
                            raise ValueError("User record missing email or delivery_address")

                        item_info = items_to_single_item(payload)

                        order_body = {
                            "user_id": user_id,
                            "email": email,
                            "delivery_address": delivery_address,
                            "item": item_info["item"],
                            "quantity": item_info["quantity"],
                        }

                        result = asyncio.run(create_order(order_body))

                        event = {
                            "type": "order_created",
                            "task_id": task_id,
                            "trace_id": trace_id,
                            "timestamp": time.time(),
                            "result": result,
                        }
                        publish_json(ch, EVENTS_ORDER_QUEUE, event)

                        order_id = None
                        if isinstance(result, dict):
                            order_id = result.get("id") or result.get("order_id")

                        result_msg = {
                            "request_id": request_id,
                            "task_id": task_id,
                            "ok": True,
                            "data": {},
                            "error": None,
                        }
                        if order_id:
                            result_msg["data"]["order_id"] = order_id
                        result_msg["data"]["raw"] = result

                        publish_json(ch, RESULTS_QUEUE, result_msg)

                        print("[OrderAgent] ✅ Order placed. Published order_created + result(ok=True)")
                        ch.basic_ack(delivery_tag=method.delivery_tag)
                        return

                    if task_type == "checkout":
                        order_id = payload.get("order_id")
                        if not order_id:
                            raise ValueError("checkout payload missing 'order_id'")

                        result = asyncio.run(checkout_order(order_id))

                        event = {
                            "type": "order_checked_out",
                            "task_id": task_id,
                            "trace_id": trace_id,
                            "timestamp": time.time(),
                            "result": result,
                        }
                        publish_json(ch, EVENTS_ORDER_QUEUE, event)

                        result_msg = {
                            "request_id": request_id,
                            "task_id": task_id,
                            "ok": True,
                            "data": {"order_id": order_id, "raw": result},
                            "error": None,
                        }
                        publish_json(ch, RESULTS_QUEUE, result_msg)

                        print("[OrderAgent] ✅ Checkout done. Published order_checked_out + result(ok=True)")
                        ch.basic_ack(delivery_tag=method.delivery_tag)
                        return

                    raise ValueError(f"Unknown task type: {task_type}")

                except Exception as e:
                    print(f"[OrderAgent] ❌ Error: {e}")

                    fail_msg = {
                        "request_id": request_id,
                        "task_id": task_id,
                        "ok": False,
                        "data": {},
                        "error": str(e),
                    }
                    publish_json(ch, RESULTS_QUEUE, fail_msg)

                    if retries + 1 >= MAX_RETRIES:
                        task["error"] = str(e)
                        task["retries"] = retries + 1
                        publish_json(ch, DEAD_ORDER_QUEUE, task)
                        print(f"[OrderAgent] 🪦 Sent to dead queue after {task['retries']} tries")
                        ch.basic_ack(delivery_tag=method.delivery_tag)
                    else:
                        task["retries"] = retries + 1
                        time.sleep(RETRY_DELAY_SEC)
                        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

            channel.basic_consume(queue=TASKS_ORDER_QUEUE, on_message_callback=callback)
            channel.start_consuming()

        except Exception as e:
            print(f"[OrderAgent] Connection error: {e}. Retrying in {RETRY_DELAY_SEC}s...")
            time.sleep(RETRY_DELAY_SEC)


if __name__ == "__main__":
    main()
