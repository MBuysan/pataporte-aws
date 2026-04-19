from pydantic import BaseModel
from datetime import date, datetime
from typing import Optional
from enum import Enum


class EstadoEsquemaEnum(str, Enum):
    activo = "activo"
    completado = "completado"
    atrasado = "atrasado"


class EstadoCertificadoEnum(str, Enum):
    vigente = "vigente"
    pendiente_revision = "pendiente_revision"
    vencido = "vencido"
    revocado = "revocado"


# ── Lo que se recibe al REGISTRAR una dosis ────────────────
class DosisCreate(BaseModel):
    id_esquema: str
    numero_dosis: int
    fecha_aplicacion: date
    lote_vacuna: Optional[str] = None
    via_administracion: Optional[str] = None
    observaciones: Optional[str] = None
    es_externa: bool = False

    class Config:
        json_schema_extra = {
            "example": {
                "id_esquema": "uuid-del-esquema",
                "numero_dosis": 1,
                "fecha_aplicacion": "2024-05-10",
                "lote_vacuna": "LOT-2024-XZ",
                "via_administracion": "subcutanea",
                "es_externa": False,
            }
        }


# ── Lo que se DEVUELVE al consultar una dosis ──────────────
class DosisResponse(BaseModel):
    id_dosis: str
    id_esquema: str
    id_veterinaria: str
    numero_dosis: int
    fecha_aplicacion: date
    fecha_programada: Optional[date]
    lote_vacuna: Optional[str]
    via_administracion: Optional[str]
    es_externa: bool

    class Config:
        from_attributes = True


# ── Lo que se DEVUELVE al consultar un certificado ─────────
class CertificadoResponse(BaseModel):
    id_certificado: str
    id_dosis: str
    estado: EstadoCertificadoEnum
    fecha_emision: datetime
    fecha_vencimiento: Optional[date]
    hash_verificacion: str
    url_documento: Optional[str]
    certificacion_manual: bool

    class Config:
        from_attributes = True


# ── Lo que se DEVUELVE al consultar un esquema completo ────
# Incluye las dosis y el certificado de cada una
class EsquemaVacunacionResponse(BaseModel):
    id_esquema: str
    id_mascota: str
    nombre_vacuna: str
    fecha_inicio: date
    estado: EstadoEsquemaEnum
    fecha_proxima_dosis: Optional[date]
    dosis: list[DosisResponse] = []

    class Config:
        from_attributes = True
