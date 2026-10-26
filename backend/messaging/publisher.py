import json
import pika
from messaging.rabbitmq import obtener_canal


def publicar_email(data: dict):
    channel, connection = obtener_canal()
    try:
        channel.basic_publish(
            exchange="", routing_key="emails", body=json.dumps(data), mandatory=True,
            properties=pika.BasicProperties(delivery_mode=2, content_type="application/json"),
        )
    finally:
        connection.close()
