"""Publicador outbox: entrega al menos una vez; ID estable ante reintentos."""
import json
import logging
import time
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from config.models import OutboxEvent

logger = logging.getLogger(__name__)


def send(envelope):
    from config.messaging import messaging_settings as settings
    body = json.dumps(envelope, ensure_ascii=False)
    if settings.MESSAGE_TRANSPORT == "sqs":
        import boto3
        from botocore.config import Config
        if not settings.SQS_QUEUE_URL:
            raise ValueError("Falta SQS_QUEUE_URL")
        boto3.client("sqs", region_name=settings.AWS_REGION,
                     config=Config(connect_timeout=3, read_timeout=10, retries={"max_attempts": 2})).send_message(
                         QueueUrl=settings.SQS_QUEUE_URL, MessageBody=body)
    elif settings.MESSAGE_TRANSPORT == "rabbitmq":
        import pika
        from messaging.rabbitmq import obtener_canal
        channel, connection = obtener_canal()
        try:
            channel.basic_publish(exchange="", routing_key="emails", body=body, mandatory=True,
                                  properties=pika.BasicProperties(delivery_mode=2, content_type="application/json",
                                                                  message_id=envelope["event_id"]))
        finally:
            connection.close()
    else:
        raise ValueError("Transporte de avisos desconocido")


def dispatch_batch(session_factory, sender=send, batch_size=10):
    count = 0
    with session_factory() as db, db.begin():
        events = db.scalars(select(OutboxEvent).where(
            OutboxEvent.dispatched_at.is_(None), OutboxEvent.available_at <= datetime.now(timezone.utc)
        ).order_by(OutboxEvent.available_at, OutboxEvent.id).limit(batch_size).with_for_update(skip_locked=True)).all()
        for event in events:
            event.attempts += 1
            try:
                sender({"schema_version": 1, "event_id": event.id, "payload": event.payload})
            except Exception:
                event.last_error = "broker_unavailable"
                event.available_at = datetime.now(timezone.utc) + timedelta(seconds=min(300, 2 ** min(event.attempts, 8)))
                logger.warning("Publicación pendiente event_id=%s", event.id)
            else:
                event.dispatched_at = datetime.now(timezone.utc)
                event.last_error = None
                # El broker ya conserva la copia durable; no retener códigos ni datos clínicos aquí.
                event.payload = {}
                count += 1
    return count


def main():
    from config.db_connection import DatabaseSettings
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    config = DatabaseSettings()
    engine = create_engine(config.sqlalchemy_url(), pool_pre_ping=True,
                           connect_args=config.database_connect_args())
    SessionLocal = sessionmaker(bind=engine)
    logging.basicConfig(level=logging.INFO)
    while True:
        try:
            dispatch_batch(SessionLocal)
        except Exception:
            logger.error("No se pudo procesar outbox; se reintentará")
        time.sleep(2)


if __name__ == "__main__":
    main()
