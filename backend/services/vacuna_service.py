import uuid
import hashlib
from datetime import date, timedelta
from sqlalchemy.orm import Session
from fastapi import HTTPException

from schemas.vacuna import DosisCreate
from config.database import Dosis, EsquemaVacunacion, Certificado


def registrar_dosis(db: Session, data: DosisCreate, id_veterinaria: str):
    """
    Registra la aplicacion de una dosis y genera su certificado automaticamente.
    Si la dosis es externa (es_externa=True), el certificado queda en
    estado 'pendiente_revision' hasta que un admin lo valide (regla 3.4.5).
    """
    pass


def esquema_por_mascota(db: Session, id_mascota: str):
    """Retorna todos los esquemas de vacunacion de una mascota con sus dosis."""
    pass


def _generar_certificado(db: Session, dosis: Dosis):
    """
    Funcion privada. Genera el certificado de la dosis.
    - Vet interno: estado = 'vigente'
    - Vet externo: estado = 'pendiente_revision' (regla 3.4.5)
    """
    pass


def _actualizar_proxima_dosis(db: Session, dosis: Dosis):
    """
    Funcion privada. Recalcula la fecha de la proxima dosis en el esquema
    usando el intervalo definido en TipoVacunas.
    """
    pass
