import json
import logging
import time
import pika
from messaging.rabbitmq import obtener_canal
from services.auth_service import _enviar_email_verificacion, _enviar_email_recuperacion
from services.pataporte_service import _enviar_pdf_por_email, _generar_pdf

logger = logging.getLogger(__name__)


def procesar(data):
    tipo = data["tipo"]
    if tipo == "verificacion_email":
        _enviar_email_verificacion(data["email"], data["codigo"])
    elif tipo == "recuperacion_password":
        _enviar_email_recuperacion(data["email"], data["codigo"])
    elif tipo == "pdf_email":
        pdf = _generar_pdf(data["credencial"], data["hash_verificacion"])
        _enviar_pdf_por_email(data["email"], data["nombre_mascota"], pdf)
    else:
        raise ValueError("Tipo de mensaje no soportado")


def callback(channel, method, properties, body):
    try:
        procesar(json.loads(body))
    except Exception:
        # En este hito local los fallos van a una cola inspeccionable, sin bucle infinito.
        logger.error("Correo fallido: revisar emails.failed; no se confirma como enviado")
        channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
    else:
        channel.basic_ack(delivery_tag=method.delivery_tag)


def main():
    logging.basicConfig(level=logging.INFO)
    while True:
        connection = None
        try:
            channel, connection = obtener_canal()
            channel.basic_qos(prefetch_count=1)
            channel.basic_consume(queue="emails", on_message_callback=callback)
            logger.info("Worker listo")
            channel.start_consuming()
        except pika.exceptions.AMQPError:
            logger.warning("RabbitMQ desconectado; reconectando")
            time.sleep(3)
        finally:
            if connection and connection.is_open:
                connection.close()


if __name__ == "__main__":
    main()
