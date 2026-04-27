import uuid
from datetime import datetime
from sqlalchemy.orm import Session
from fastapi import HTTPException

from schemas.tratamiento import TratamientoCreate, TratamientoUpdate
from config.database import Tratamiento, Mascota


def editar_tratamiento(db: Session, data: TratamientoCreate) -> Tratamiento:
    """
    Registra un nuevo tratamiento para una mascota.
    Verifica que la mascota exista y esté activa.
    Regla: no puede haber dos tratamientos con el mismo nombre para la misma mascota.
    """
    pass


def ver_tratamientos_activos(db: Session, id_mascota: str) -> list[Tratamiento]:
    """
    Retorna los tratamientos activos (sin fecha de finalización o con fecha futura)
    de una mascota, ordenados del más reciente al más antiguo.
    """
    pass


def listar_por_mascota(db: Session, id_mascota: str) -> list[Tratamiento]:
    """
    Retorna todos los tratamientos (activos e históricos) de una mascota.
    """
    pass


def obtener_por_id(db: Session, id_tratamiento: str) -> Tratamiento:
    """Busca un tratamiento por UUID."""
    pass


def actualizar(
    db: Session, id_tratamiento: str, data: TratamientoUpdate
) -> Tratamiento:
    """Actualiza descripción o fecha de finalización de un tratamiento."""
    pass
