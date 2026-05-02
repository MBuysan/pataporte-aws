from pydantic import BaseModel, Field
from datetime import date, datetime
from typing import Optional, List
from enum import Enum
from typing import List

class EstadoEsquemaEnum(str, Enum):
    activo = "activo"
    completado = "completado"
    atrasado = "atrasado"


class EstadoCertificadoEnum(str, Enum):
    vigente = "vigente"
    pendiente_revision = "pendiente_revision"
    vencido = "vencido"
    revocado = "revocado"

class VacunaResponse(BaseModel):
    id_esquema_vacuna: str
    id_vacuna: str
    nombre: str

    estado: str   
    fecha_inicio: date
    fecha_proxima_dosis: Optional[date]

    dosis: List[DosisResponse] = Field(default_factory=list)

    class Config:
        from_attributes = True

class EsquemaVacunacionResponse(BaseModel):
    id_esquema: str
    id_mascota: str

    vacunas: List[VacunaResponse] = Field(default_factory=list)

    class Config:
        from_attributes = True

# ── Certificado primero (lo usa DosisResponse) ─────────────
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


# ── Lo que se recibe al REGISTRAR una dosis ────────────────
class DosisCreate(BaseModel):
    id_esquema_vacuna: str   #antes era id_esquema
    numero_dosis: int
    fecha_aplicacion: date
    lote_vacuna: Optional[str] = None
    via_administracion: Optional[str] = None
    observaciones: Optional[str] = None
    es_externa: bool = False


# ── Dosis (usa CertificadoResponse) ───────────────────────
class DosisResponse(BaseModel):
    id_dosis: str
    id_esquema_vacuna: str
    id_veterinaria: str
    numero_dosis: int
    fecha_aplicacion: date
    fecha_programada: Optional[date]
    lote_vacuna: Optional[str]
    via_administracion: Optional[str]
    es_externa: bool

    certificado: Optional[CertificadoResponse] = None

    class Config:
        from_attributes = True


# ── Vacuna (usa DosisResponse) ────────────────────────────
class VacunaResponse(BaseModel):
    id_esquema_vacuna: str
    id_vacuna: str
    nombre: str
    estado: str
    fecha_inicio: date
    fecha_proxima_dosis: Optional[date]

    dosis: List[DosisResponse] = Field(default_factory=list)

    class Config:
        from_attributes = True


# ── Esquema (usa VacunaResponse) ──────────────────────────
class EsquemaVacunacionResponse(BaseModel):
    id_esquema: str
    id_mascota: str

    vacunas: List[VacunaResponse] = Field(default_factory=list)

    class Config:
        from_attributes = True
