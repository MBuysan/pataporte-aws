import json
from functools import cache

import boto3

from config.settings import settings

FUENTE = "pataporte.api"


@cache
def _cliente(servicio: str):
    return boto3.client(servicio, region_name=settings.AWS_REGION)


def publicar_evento(nombre: str, detalle: dict):
    """
    Publica un evento de dominio.
    Con EVENT_BUS_NAME va a EventBridge; sin él, se manda directo a la cola SQS
    con la misma forma que tendría el evento de EventBridge (source/detail-type/detail).
    """
    if settings.EVENT_BUS_NAME:
        respuesta = _cliente("events").put_events(Entries=[{
            "EventBusName": settings.EVENT_BUS_NAME,
            "Source": FUENTE,
            "DetailType": nombre,
            "Detail": json.dumps(detalle),
        }])
        if respuesta.get("FailedEntryCount"):
            raise RuntimeError(f"EventBridge rechazó el evento {nombre}: {respuesta['Entries']}")
        return

    _cliente("sqs").send_message(
        QueueUrl=settings.QUEUE_URL,
        MessageBody=json.dumps({"source": FUENTE, "detail-type": nombre, "detail": detalle}),
    )
