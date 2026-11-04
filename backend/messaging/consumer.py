import json
import logging
import time
from datetime import datetime, timezone
from email.parser import Parser
import pika
from messaging.rabbitmq import obtener_canal
from messaging.delivery import _enviar_email_verificacion, _enviar_email_recuperacion, _enviar_pdf_por_email, _generar_pdf

logger = logging.getLogger(__name__)


def procesar(data):
    data = data.get("payload", data)
    if data.get("expires_at") and datetime.fromisoformat(data["expires_at"]) <= datetime.now(timezone.utc):
        return
    tipo = data["tipo"]
    if tipo == "verificacion_email":
        _enviar_email_verificacion(data["email"], data["codigo"])
    elif tipo == "recuperacion_password":
        _enviar_email_recuperacion(data["email"], data["codigo"])
    elif tipo == "pdf_email":
        pdf = _generar_pdf(data["credencial"], data["hash_verificacion"])
        _enviar_pdf_por_email(data["email"], data["nombre_mascota"], pdf)
    elif tipo == "raw_email":
        from utils.email import enviar_email
        enviar_email(data["email"], Parser().parsestr(data["mime"]))
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
