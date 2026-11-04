import json
import logging
import threading
import time

from botocore.exceptions import ClientError

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


DEDUP_TTL_SEGUNDOS = 7 * 24 * 3600


def _reservar(id_evento) -> bool:
    """Registra el id en DynamoDB si no estaba. False = ya se procesó (o se está procesando)."""
    if not settings.DEDUP_TABLE or not id_evento:
        return True
    try:
        _cliente("dynamodb").put_item(
            TableName=settings.DEDUP_TABLE,
            Item={"id_evento": {"S": id_evento}, "expira": {"N": str(int(time.time()) + DEDUP_TTL_SEGUNDOS)}},
            ConditionExpression="attribute_not_exists(id_evento)",
        )
        return True
    except ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            return False
        raise


def _liberar(id_evento):
    if settings.DEDUP_TABLE and id_evento:
        _cliente("dynamodb").delete_item(TableName=settings.DEDUP_TABLE, Key={"id_evento": {"S": id_evento}})


def procesar(body: str) -> bool:
    """
    Procesa un evento una sola vez por id_evento. Devuelve False si era un duplicado.
    ponytail: si el worker muere entre reservar y terminar, el reintento se descarta como
    duplicado; agregar un lease (estado + vencimiento) si eso llega a importar.
    """
    evento = json.loads(body)
    id_evento = evento["detail"].get("id_evento")
    if not _reservar(id_evento):
        return False
    try:
        MANEJADORES[evento["detail-type"]](evento["detail"])
    except Exception:
        _liberar(id_evento)
        raise
    return True


def procesar_mensajes(sqs):
    """Un long-poll. Borra el mensaje si se procesó bien o era duplicado; si falla, SQS lo reintenta y luego va a la DLQ."""
    respuesta = sqs.receive_message(QueueUrl=settings.QUEUE_URL, MaxNumberOfMessages=10, WaitTimeSeconds=20)
    for mensaje in respuesta.get("Messages", []):
        try:
            if not procesar(mensaje["Body"]):
                logger.info("Mensaje %s duplicado, se descarta", mensaje.get("MessageId"))
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
    _cliente("dynamodb")
    threading.Thread(target=bucle_despachador, name="outbox", daemon=True).start()
    while True:
        procesar_mensajes(sqs)
