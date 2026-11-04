import json

from config.settings import settings
from messaging import consumer, publisher


class ClienteFalso:
    def __init__(self, mensajes=()):
        self.llamadas = []
        self.mensajes = list(mensajes)

    def send_message(self, **kw):
        self.llamadas.append(("send_message", kw))

    def put_events(self, **kw):
        self.llamadas.append(("put_events", kw))
        return {"FailedEntryCount": 0, "Entries": [{"EventId": "1"}]}

    def receive_message(self, **kw):
        self.llamadas.append(("receive_message", kw))
        return {"Messages": self.mensajes}

    def delete_message(self, **kw):
        self.llamadas.append(("delete_message", kw))


def test_publica_sobre_tipo_eventbridge_directo_a_sqs(monkeypatch):
    falso = ClienteFalso()
    monkeypatch.setattr(publisher, "_cliente", lambda servicio: falso)
    monkeypatch.setattr(settings, "EVENT_BUS_NAME", "")

    publisher.enviar("ev-1", "PataporteEmitido", {"email": "a@b.c"})

    [(metodo, kw)] = falso.llamadas
    assert metodo == "send_message"
    assert kw["QueueUrl"] == settings.QUEUE_URL
    assert json.loads(kw["MessageBody"]) == {
        "source": "pataporte.api",
        "detail-type": "PataporteEmitido",
        "detail": {"email": "a@b.c", "id_evento": "ev-1"},
    }


def test_publica_en_eventbridge_si_hay_bus(monkeypatch):
    falso = ClienteFalso()
    monkeypatch.setattr(publisher, "_cliente", lambda servicio: falso)
    monkeypatch.setattr(settings, "EVENT_BUS_NAME", "bus-pataporte")

    publisher.enviar("ev-2", "MascotaEliminada", {"pdf_key": "x.pdf"})

    [(metodo, kw)] = falso.llamadas
    assert metodo == "put_events"
    [entrada] = kw["Entries"]
    assert entrada["EventBusName"] == "bus-pataporte"
    assert entrada["Source"] == "pataporte.api"
    assert entrada["DetailType"] == "MascotaEliminada"
    assert json.loads(entrada["Detail"]) == {"pdf_key": "x.pdf", "id_evento": "ev-2"}


def test_worker_despacha_por_detail_type_y_borra_solo_los_exitosos(monkeypatch):
    recibidos = []
    monkeypatch.setitem(consumer.MANEJADORES, "VerificacionEmailSolicitada", recibidos.append)

    def explota(detalle):
        raise RuntimeError("smtp caído")

    monkeypatch.setitem(consumer.MANEJADORES, "PataporteEmitido", explota)

    sobre = lambda tipo: json.dumps({"source": "pataporte.api", "detail-type": tipo, "detail": {"email": "a@b.c"}})
    sqs = ClienteFalso([
        {"MessageId": "1", "ReceiptHandle": "ok", "Body": sobre("VerificacionEmailSolicitada")},
        {"MessageId": "2", "ReceiptHandle": "falla", "Body": sobre("PataporteEmitido")},
        {"MessageId": "3", "ReceiptHandle": "desconocido", "Body": sobre("TipoInexistente")},
    ])

    consumer.procesar_mensajes(sqs)

    assert recibidos == [{"email": "a@b.c"}]
    borrados = [kw["ReceiptHandle"] for metodo, kw in sqs.llamadas if metodo == "delete_message"]
    assert borrados == ["ok"]
    [(_, recepcion)] = [c for c in sqs.llamadas if c[0] == "receive_message"]
    assert recepcion["WaitTimeSeconds"] == 20


def test_detail_types_conocidos():
    assert set(consumer.MANEJADORES) == {
        "VerificacionEmailSolicitada",
        "RecuperacionPasswordSolicitada",
        "PataporteEmitido",
        "MascotaEliminada",
    }


class DynamoFalso:
    """put_item condicional (attribute_not_exists) y delete_item sobre un dict."""
    def __init__(self):
        self.items = {}

    def put_item(self, TableName, Item, ConditionExpression):
        from botocore.exceptions import ClientError
        clave = Item["id_evento"]["S"]
        if clave in self.items:
            raise ClientError({"Error": {"Code": "ConditionalCheckFailedException"}}, "PutItem")
        self.items[clave] = Item

    def delete_item(self, TableName, Key):
        self.items.pop(Key["id_evento"]["S"], None)


def test_worker_deduplica_por_id_evento_y_libera_si_falla(monkeypatch):
    dynamo = DynamoFalso()
    monkeypatch.setattr(consumer, "_cliente", lambda servicio: dynamo)
    monkeypatch.setattr(settings, "DEDUP_TABLE", "pataporte-entregas")
    recibidos = []
    monkeypatch.setitem(consumer.MANEJADORES, "VerificacionEmailSolicitada", recibidos.append)
    sobre = lambda tipo, id_evento: json.dumps({"detail-type": tipo, "detail": {"id_evento": id_evento}})

    sqs = ClienteFalso([
        {"MessageId": "1", "ReceiptHandle": "a", "Body": sobre("VerificacionEmailSolicitada", "e1")},
        {"MessageId": "2", "ReceiptHandle": "b", "Body": sobre("VerificacionEmailSolicitada", "e1")},
        {"MessageId": "3", "ReceiptHandle": "c", "Body": sobre("TipoInexistente", "e2")},
    ])
    consumer.procesar_mensajes(sqs)

    assert len(recibidos) == 1  # el duplicado no se procesa
    borrados = [kw["ReceiptHandle"] for metodo, kw in sqs.llamadas if metodo == "delete_message"]
    assert borrados == ["a", "b"]  # el duplicado sí se borra de la cola
    assert set(dynamo.items) == {"e1"}  # e2 falló: se liberó para que el reintento corra
    assert int(dynamo.items["e1"]["expira"]["N"]) > 0
