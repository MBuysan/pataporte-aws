import pika
from config.settings import settings

import time

def obtener_canal():
    last_error = None

    for i in range(20):  # intenta por ~1 minuto
        try:
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(
                    host="rabbitmq",
                    heartbeat=600,
                    blocked_connection_timeout=300
                )
            )

            channel = connection.channel()
            channel.queue_declare(queue="emails", durable=True)

            print("Conectado a RabbitMQ ✔")
            return channel, connection

        except Exception as e:
            last_error = e
            print(f"RabbitMQ no listo... intento {i+1}/20")
            time.sleep(3)

    raise Exception(f"No se pudo conectar a RabbitMQ: {last_error}")