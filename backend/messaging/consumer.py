import json
import logging
import threading

from config.settings import settings
from messaging.publisher import _cliente, bucle_despachador
from services import auth_service, mascota_service, pataporte_service, storage_service

logger = logging.getLogger("pataporte.worker")


def _pataporte_emitido(d):
    pdf = pataporte_service.generar_pdf(d["credencial"], d["hash_verificacion"])
    pataporte_service.enviar_pdf_por_email(d["email"], d["nombre_mascota"], pdf)


def _mascota_eliminada(d):
    pdf = storage_service.descargar(d["pdf_key"])
    mascota_service.enviar_historial_por_email(d["email"], d["nombre_mascota"], pdf)


# detail-type -> manejador(detail)
MANEJADORES = {
    "VerificacionEmailSolicitada": lambda d: auth_service.enviar_email_verificacion(d["email"], d["codigo"]),
    "RecuperacionPasswordSolicitada": lambda d: auth_service.enviar_email_recuperacion(d["email"], d["codigo"]),
    "PataporteEmitido": _pataporte_emitido,
    "MascotaEliminada": _mascota_eliminada,
}


def procesar(body: str):
    evento = json.loads(body)
    MANEJADORES[evento["detail-type"]](evento["detail"])


def procesar_mensajes(sqs):
    """Un long-poll. Borra el mensaje solo si se procesó bien; si falla, SQS lo reintenta y luego va a la DLQ."""
    respuesta = sqs.receive_message(QueueUrl=settings.QUEUE_URL, MaxNumberOfMessages=10, WaitTimeSeconds=20)
    for mensaje in respuesta.get("Messages", []):
        try:
            procesar(mensaje["Body"])
        except Exception:
            logger.exception("Error procesando mensaje %s", mensaje.get("MessageId"))
            continue
        sqs.delete_message(QueueUrl=settings.QUEUE_URL, ReceiptHandle=mensaje["ReceiptHandle"])


if __name__ == "__main__":
    logging.basicConfig(level=settings.LOG_LEVEL)
    logger.info("Worker escuchando %s", settings.QUEUE_URL)
    sqs = _cliente("sqs")
    # clientes boto3 creados acá: crearlos en paralelo desde dos hilos no es seguro
    _cliente("events" if settings.EVENT_BUS_NAME else "sqs")
    threading.Thread(target=bucle_despachador, name="outbox", daemon=True).start()
    while True:
        procesar_mensajes(sqs)
