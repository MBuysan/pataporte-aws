from pydantic import BaseModel
from datetime import date, datetime
from typing import Optional, List

from schemas.vacuna import EsquemaVacunacionResponse, CertificadoResponse


# ── Información resumida del tutor para el pataporte ──────
class TutorResumenResponse(BaseModel):
    id_tutor: str
    nombre: str
    cedula: str
    email: str
    telefono: Optional[str]

    class Config:
        from_attributes = True


# ── Lo que se DEVUELVE al ver el pataporte ────────────────
class PataporteResponse(BaseModel):
    id_mascota: str
    nombre: str
    especie: str
    raza: Optional[str]
    fecha_de_nacimiento: Optional[date]
    sexo: str
    foto_url: Optional[str]
    tutor_principal: Optional[TutorResumenResponse]
    esquemas_vacunacion: List[EsquemaVacunacionResponse] = []

    class Config:
        from_attributes = True


# ── Lo que se DEVUELVE al generar un certificado de vacunas ─
class CertificadoVacunasResponse(BaseModel):
    id_certificado: str
    id_mascota: str
    nombre_mascota: str
    fecha_generacion: datetime
    certificados: List[CertificadoResponse] = []

    class Config:
        from_attributes = True
