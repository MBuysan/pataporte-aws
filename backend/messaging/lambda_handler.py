"""SQS → Lambda con exclusión temporal y deduplicación durable en DynamoDB."""
from datetime import datetime, timezone
from functools import lru_cache
import hashlib
import json
import logging
import os
import time
from uuid import UUID, uuid4

import boto3
from botocore.exceptions import ClientError
from botocore.config import Config

logger = logging.getLogger(__name__)
KINDS = {"verificacion_email", "recuperacion_password", "pdf_email", "raw_email", "probe"}


@lru_cache(maxsize=2)
def client(service):
    return boto3.client(service, config=Config(connect_timeout=3, read_timeout=10,
                                              retries={"mode": "standard", "max_attempts": 2}))


def deliver(payload, event_id):
    """Sin acceso a PostgreSQL: el evento lleva una instantánea de los datos."""
    from messaging.delivery import (_enviar_email_verificacion, _enviar_email_recuperacion,
                                    _generar_pdf, _enviar_pdf_por_email)
    kind = payload["tipo"]
    if kind == "probe":
        client("s3").put_object(Bucket=os.environ["ASSETS_BUCKET"], Key=f"probes/{event_id}.json",
                                Body=b'{"status":"processed"}', ContentType="application/json", ServerSideEncryption="AES256")
        return
    if payload.get("expires_at"):
        expiration = datetime.fromisoformat(payload["expires_at"])
        if expiration.tzinfo is None:
            raise ValueError("El vencimiento debe incluir zona horaria")
        if expiration <= datetime.now(timezone.utc):
            return
    if kind == "verificacion_email":
        _enviar_email_verificacion(payload["email"], payload["codigo"])
    elif kind == "recuperacion_password":
        _enviar_email_recuperacion(payload["email"], payload["codigo"])
    elif kind == "pdf_email":
        pdf = _generar_pdf(payload["credencial"], payload["hash_verificacion"])
        client("s3").put_object(Bucket=os.environ["ASSETS_BUCKET"], Key=f"certificates/{event_id}.pdf",
                                Body=pdf, ContentType="application/pdf", ServerSideEncryption="AES256")
        _enviar_pdf_por_email(payload["email"], payload["nombre_mascota"], pdf)
    elif kind == "raw_email":
        from email.parser import Parser
        from utils.email import enviar_email
        enviar_email(payload["email"], Parser().parsestr(payload["mime"]))


def process(envelope, dynamodb=None, delivery=deliver, now=None):
    if envelope.get("schema_version") != 1 or not isinstance(envelope.get("payload"), dict):
        raise ValueError("Versión o estructura de evento inválida")
    event_id = str(UUID(envelope["event_id"]))
    payload = envelope["payload"]
    if payload.get("tipo") not in KINDS:
        raise ValueError("Tipo de evento no soportado")
    fingerprint = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()
    token = str(uuid4())
    now = int(time.time() if now is None else now)
    dynamodb = dynamodb or client("dynamodb")
    table = os.environ["IDEMPOTENCY_TABLE"]
    key = {"event_id": {"S": event_id}}
    owner = {":token": {"S": token}}
    try:
        dynamodb.put_item(TableName=table, Item={**key, "status": {"S": "PROCESSING"}, "token": {"S": token},
                          "fingerprint": {"S": fingerprint}, "lease_until": {"N": str(now + 120)}, "expires_at": {"N": str(now + 30 * 86400)}},
                          ConditionExpression="attribute_not_exists(event_id) OR (#status = :processing AND lease_until < :now)",
                          ExpressionAttributeNames={"#status": "status"},
                          ExpressionAttributeValues={":processing": {"S": "PROCESSING"}, ":now": {"N": str(now)}})
    except ClientError as exc:
        if exc.response["Error"]["Code"] != "ConditionalCheckFailedException":
            raise
        previous = dynamodb.get_item(TableName=table, Key=key, ConsistentRead=True).get("Item", {})
        if previous.get("status", {}).get("S") == "DONE" and previous.get("fingerprint", {}).get("S") == fingerprint:
            return "duplicate"
        raise RuntimeError("Evento en proceso o ID reutilizado con otro contenido") from None
    try:
        delivery(payload, event_id)
        dynamodb.update_item(TableName=table, Key=key, UpdateExpression="SET #status = :done REMOVE #token, lease_until",
                             ConditionExpression="#token = :token", ExpressionAttributeNames={"#status": "status", "#token": "token"},
                             ExpressionAttributeValues={**owner, ":done": {"S": "DONE"}})
    except Exception:
        try:
            dynamodb.delete_item(TableName=table, Key=key, ConditionExpression="#token = :token",
                                 ExpressionAttributeNames={"#token": "token"}, ExpressionAttributeValues=owner)
        except ClientError:
            pass
        raise
    return "processed"


def handler(event, context):
    failed = []
    for record in event.get("Records", []):
        try:
            process(json.loads(record["body"]))
        except Exception:
            # Sin cuerpos, direcciones, códigos ni excepciones que puedan incluir datos clínicos.
            logger.error("Evento fallido message_id=%s", record.get("messageId", "unknown"))
            failed.append({"itemIdentifier": record["messageId"]})
    return {"batchItemFailures": failed}
