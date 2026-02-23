import os
import json
import time
from typing import Any, Dict, Optional, Tuple

import pika
from fastapi import HTTPException

# -------------------------------------------------
# RabbitMQ configuration
# -------------------------------------------------
RABBIT_URL = os.getenv("RABBIT_URL", "amqp://guest:guest@localhost:5672/")

RABBIT_CONNECT_RETRIES = int(os.getenv("RABBIT_CONNECT_RETRIES", "10"))
RABBIT_CONNECT_RETRY_DELAY_SEC = float(os.getenv("RABBIT_CONNECT_RETRY_DELAY_SEC", "1.0"))

# -------------------------------------------------
# Connection helper (NEW)
# -------------------------------------------------
def connect() -> pika.BlockingConnection:
    """
    Create a RabbitMQ connection with retries (useful for local startup race conditions).
    """
    last_error: Optional[Exception] = None
    for _ in range(RABBIT_CONNECT_RETRIES):
        try:
            params = pika.URLParameters(RABBIT_URL)
            return pika.BlockingConnection(params)
        except Exception as e:
            last_error = e
            time.sleep(RABBIT_CONNECT_RETRY_DELAY_SEC)

    raise HTTPException(
        status_code=503,
        detail=f"Failed to connect to RabbitMQ at '{RABBIT_URL}': {last_error}",
    )

# -------------------------------------------------
# Publish helper (EXISTING)
# -------------------------------------------------
def publish_json(queue_name: str, message: Dict[str, Any]) -> None:
    """
    Publish a JSON message to RabbitMQ.

    - Queue is durable (survives broker restart)
    - Message is persistent (saved to disk)
    - Retries on startup race conditions
    """
    body = json.dumps(message).encode("utf-8")
    last_error: Optional[Exception] = None

    for _ in range(RABBIT_CONNECT_RETRIES):
        try:
            connection = connect()
            channel = connection.channel()

            channel.queue_declare(queue=queue_name, durable=True)

            channel.basic_publish(
                exchange="",
                routing_key=queue_name,
                body=body,
                properties=pika.BasicProperties(
                    delivery_mode=2,  # persistent
                    content_type="application/json",
                ),
            )

            connection.close()
            return

        except Exception as e:
            last_error = e
            time.sleep(RABBIT_CONNECT_RETRY_DELAY_SEC)

    raise HTTPException(
        status_code=503,
        detail=f"Failed to publish message to RabbitMQ queue '{queue_name}': {last_error}",
    )

# -------------------------------------------------
# Consume one message helper (NEW)
# -------------------------------------------------
def get_one_json(
    queue_name: str,
    *,
    auto_ack: bool = False,
) -> Tuple[Optional[Dict[str, Any]], Optional[pika.spec.Basic.Deliver], Optional[pika.channel.Channel], Optional[pika.BlockingConnection]]:
    """
    Read ONE message from a queue (non-blocking) using basic_get.

    Returns:
      (message_dict_or_None, method_frame_or_None, channel_or_None, connection_or_None)

    If no message is present, returns (None, None, None, None).
    Caller is responsible for ack/nack and closing connection.
    """
    connection = connect()
    channel = connection.channel()
    channel.queue_declare(queue=queue_name, durable=True)

    method_frame, properties, body = channel.basic_get(queue=queue_name, auto_ack=auto_ack)

    if method_frame is None:
        try:
            connection.close()
        except Exception:
            pass
        return None, None, None, None

    try:
        msg = json.loads(body.decode("utf-8"))
    except Exception:
        # Bad JSON; caller can ack and drop it
        msg = {"_raw": body.decode("utf-8", errors="replace")}

    return msg, method_frame, channel, connection

# -------------------------------------------------
# Ack helpers (NEW)
# -------------------------------------------------
def ack(channel: pika.channel.Channel, delivery_tag: int) -> None:
    channel.basic_ack(delivery_tag=delivery_tag)

def nack(channel: pika.channel.Channel, delivery_tag: int, *, requeue: bool = True) -> None:
    channel.basic_nack(delivery_tag=delivery_tag, requeue=requeue)
