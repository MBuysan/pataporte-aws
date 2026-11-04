import json
import logging
import time
import uuid
from datetime import datetime, timedelta, timezone
from functools import cache

import boto3
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from config.settings import settings

FUENTE = "pataporte.api"
logger = logging.getLogger("pataporte.outbox")


@cache
def _cliente(servicio: str):
    return boto3.client(servicio, region_name=settings.AWS_REGION)


def publicar_evento(db: Session, nombre: str, detalle: dict) -> str:
    """
    Registra un evento de dominio en la outbox, dentro de la sesión del llamador.
    No toca la red: el evento sale recién cuando el llamador hace commit y el
    despachador del worker lo publica. Devuelve el id del evento.
    """
    from config.database import Outbox

    id_evento = str(uuid.uuid4())
    db.add(Outbox(id=id_evento, tipo=nombre, detalle=detalle))
    return id_evento


def enviar(id_evento: str, nombre: str, detalle: dict):
    """
    Publica un evento ya confirmado.
    Con EVENT_BUS_NAME va a EventBridge; sin él, se manda directo a la cola SQS
    con la misma forma que tendría el evento de EventBridge (source/detail-type/detail).
    El id de la outbox viaja en detail.id_evento para que el worker deduplique
    (EventBridge asigna su propio id al evento).
    """
    detalle = {**detalle, "id_evento": id_evento}
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


def despachar_lote(session_factory=None, tamano: int = 10) -> int:
    """
    Publica hasta `tamano` eventos pendientes. FOR UPDATE SKIP LOCKED deja correr
    varios despachadores sin mandar dos veces la misma fila. Entrega al menos una vez:
    si el commit falla después de publicar, se reenvía y el worker deduplica por id.
    """
    from config.database import Outbox, SessionLocal

    enviados = 0
    with (session_factory or SessionLocal)() as db, db.begin():
        pendientes = db.scalars(
            select(Outbox)
            .where(Outbox.enviado.is_(None), Outbox.disponible_desde <= func.now())
            .order_by(Outbox.disponible_desde)
            .limit(tamano)
            .with_for_update(skip_locked=True)
        ).all()
        for evento in pendientes:
            evento.intentos += 1
            try:
                enviar(evento.id, evento.tipo, evento.detalle)
            except Exception as e:
                # backoff exponencial con tope de 5 minutos
                evento.ultimo_error = str(e)[:500]
                evento.disponible_desde = datetime.now(timezone.utc) + timedelta(seconds=min(300, 2 ** evento.intentos))
                logger.warning("No se pudo publicar %s (intento %s)", evento.id, evento.intentos)
            else:
                evento.enviado = datetime.now(timezone.utc)
                enviados += 1
    return enviados


def bucle_despachador():
    """
    Corre como hilo dentro del worker.
    ponytail: hilo en el worker, sin servicio ECS propio; separarlo si el throughput importa.
    ponytail: reintenta para siempre (con backoff); agregar tope + alarma si se acumulan fallidos.
    """
    while True:
        try:
            if despachar_lote():
                continue
        except Exception:
            logger.exception("Error despachando la outbox")
        time.sleep(1)
