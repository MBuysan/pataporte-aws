import json

from messaging.rabbitmq import obtener_canal
from services.auth_service import _enviar_email_verificacion

channel, connection = obtener_canal()

def callback(ch, method, properties, body):

    data = json.loads(body)
    tipo = data["tipo"]

    if tipo == "verificacion_email":
        _enviar_email_verificacion(
            data["email"],
            data["codigo"]
        )
    
    ch.basic_ack(delivery_tag=method.delivery_tag)

channel.basic_consume(
    queue="emails",
    on_message_callback=callback
)

print("Esperando mensajes...")

channel.start_consuming()