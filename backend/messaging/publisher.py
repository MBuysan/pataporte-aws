import json
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from sqlalchemy.orm import Session
from config.models import OutboxEvent


def publicar_email(data: dict, db: Session) -> str:
    """No contacta al broker ni confirma la transacción de quien llama."""
    if data.get("tipo") not in {"verificacion_email", "recuperacion_password", "pdf_email", "raw_email"}:
        raise ValueError("Tipo de aviso no soportado")
    payload = dict(data)
    if payload["tipo"] in {"verificacion_email", "recuperacion_password"}:
        payload["expires_at"] = (datetime.now(timezone.utc) + timedelta(minutes=15)).isoformat()
    if len(json.dumps(payload, ensure_ascii=False).encode("utf-8")) > 180_000:
        raise ValueError("Aviso demasiado grande para la cola")
    event_id = str(uuid4())
    db.add(OutboxEvent(id=event_id, event_type=payload["tipo"], payload=payload))
    return event_id
