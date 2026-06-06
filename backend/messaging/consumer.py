import json

from config.database import SessionLocal

from messaging.rabbitmq import obtener_canal

from services.auth_service import _enviar_email_verificacion
from services.mascota_service import (
    _enviar_historial_por_email,
    obtener_por_id,
)
from services.pataporte_service import (
    _enviar_pdf_por_email,
    _generar_pdf,
)

channel, connection = obtener_canal()


def callback(ch, method, properties, body):
    try:
        data = json.loads(body)
        tipo = data["tipo"]

        if tipo == "verificacion_email":
            _enviar_email_verificacion(
                data["email"],
                data["codigo"]
            )

        elif tipo == "pdf_email":

            pdf = _generar_pdf(
                data["credencial"],
                data["hash_verificacion"]
            )

            _enviar_pdf_por_email(
                data["email"],
                data["nombre_mascota"],
                pdf
            )

        ch.basic_ack(delivery_tag=method.delivery_tag)

    except Exception as e:
        print(f"Error procesando mensaje: {e}")


channel.basic_consume(
    queue="emails",
    on_message_callback=callback
)

print("Esperando mensajes...")

channel.start_consuming()