import pika
import json
import os
from dotenv import load_dotenv

# Load environment variables (used for Docker)
load_dotenv()

# RabbitMQ connection URL
RABBIT_URL = os.getenv("RABBIT_URL", "amqp://guest:guest@localhost:5672/")

def publish_event(event_data: dict):
    try:
        # Establish connection to RabbitMQ
        connection = pika.BlockingConnection(
            pika.URLParameters(RABBIT_URL)
        )
        channel = connection.channel()

        # Declare queue (idempotent)
        channel.queue_declare(queue="user_updates", durable=True)


        # Publish message
        channel.basic_publish(
            exchange="",
            routing_key="user_updates",
            body=json.dumps(event_data)
        )

        print(f"Event published: {event_data}")

        # Close connection
        connection.close()

    except Exception as e:
        print(f"Error connecting to RabbitMQ: {e}")

