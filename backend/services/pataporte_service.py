import uuid
from datetime import datetime
from sqlalchemy.orm import Session
from fastapi import HTTPException

from config.database import Mascota, MascotaTutor, UsuarioTutor, EsquemaVacunacion, Dosis, Certificado


def ver_pataporte(db: Session, id_mascota: str) -> dict:
    """
    Retorna el pataporte digital completo de una mascota:
    datos de identidad, tutor principal y esquemas de vacunación con sus dosis.
    """
    pass


def generar_pataporte(db: Session, id_mascota: str) -> dict:
    """
    Genera (o actualiza) el pataporte digital de una mascota.
    Alias de ver_pataporte con intención de persistencia futura
    (p. ej. generar PDF o URL pública).
    Retorna los mismos datos que ver_pataporte.
    """
    


def generar_certificado_vacunas(db: Session, id_mascota: str) -> dict:
    """
    Genera un resumen de todos los certificados de vacunación vigentes de la mascota.
    Retorna id_certificado por cada dosis certificada.
    Solo incluye certificados en estado 'vigente'.
    """
    pass
