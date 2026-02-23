import pika
import json
import os
from dotenv import load_dotenv
from app.db import orders_collection

load_dotenv()

RABBIT_URL = os.getenv("RABBIT_URL")


def handle_user_update(event):
    event_type = event.get("type")
    user_id = event.get("user_id")

    if not event_type or not user_id:
        print(" Event missing required fields:", event)
        return

    if event_type == "email_updated":
        new_email = event.get("new_email")
        print(f" Sync: Updating email for user {user_id} → {new_email}")

        result = orders_collection.update_many(
            {"user_id": user_id},
            {"$set": {"email": new_email}}
        )

        print(f" {result.modified_count} order(s) updated")

    elif event_type == "address_updated":
        new_addr = event.get("new_address")
        print(f" Sync: Updating address for user {user_id} → {new_addr}")

        result = orders_collection.update_many(
            {"user_id": user_id},
            {"$set": {"delivery_address": new_addr}}
        )

        print(f" {result.modified_count} order(s) updated")

    else:
        print(" Unknown event type:", event_type)


def callback(ch, method, properties, body):
    try:
        event = json.loads(body)
        print(f"Received event: {event}")
        handle_user_update(event)
    except Exception as e:
        print("Error handling event:", e)


def start_consumer():
    print("Connecting to RabbitMQ...")
    connection = pika.BlockingConnection(pika.URLParameters(RABBIT_URL))
    channel = connection.channel()

    channel.queue_declare(queue="user_updates", durable=True)

    print("Waiting for user update events...")
    channel.basic_consume(
        queue="user_updates",
        on_message_callback=callback,
        auto_ack=True
    )

    channel.start_consuming()


if __name__ == "__main__":
    start_consumer()
