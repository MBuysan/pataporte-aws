import json
from messaging.rabbitmq import obtener_canal
import pika

def publicar_email(data: dict):

    channel, connection = obtener_canal()

    channel.basic_publish(
        exchange="",
        routing_key="emails",
        body=json.dumps(data),
        properties=pika.BasicProperties(
            delivery_mode=2
        )
    )

    connection.close()
