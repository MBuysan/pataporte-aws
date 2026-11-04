import time
import pika
from config.messaging import messaging_settings as settings


def obtener_canal():
    for attempt in range(20):
        try:
            connection = pika.BlockingConnection(pika.ConnectionParameters(
                host=settings.RABBITMQ_HOST, port=settings.RABBITMQ_PORT,
                credentials=pika.PlainCredentials(settings.RABBITMQ_USER, settings.RABBITMQ_PASSWORD),
                heartbeat=60, blocked_connection_timeout=10, socket_timeout=5,
            ))
            channel = connection.channel()
            channel.queue_declare(queue="emails.failed", durable=True)
            channel.queue_declare(queue="emails", durable=True, arguments={
                "x-dead-letter-exchange": "",
                "x-dead-letter-routing-key": "emails.failed",
            })
            channel.confirm_delivery()
            return channel, connection
        except pika.exceptions.AMQPError:
            if attempt == 19:
                raise
            time.sleep(3)
