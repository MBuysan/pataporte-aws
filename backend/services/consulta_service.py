import uuid
from datetime import datetime
from sqlalchemy.orm import Session
from fastapi import HTTPException

from schemas.consulta import ConsultaCreate, ConsultaUpdate


def crear(db: Session, data: ConsultaCreate, id_veterinario: str):
    """
    Registra una consulta clinica.
    El id_veterinario viene del token JWT, no del body del request.
    La fecha_hora la pone el sistema, no el usuario.
    """
    pass


def listar_por_mascota(db: Session, id_mascota: str):
    """
    Retorna el historial completo de una mascota ordenado de mas reciente a mas antiguo.
    El historial pertenece a la mascota, no a la clinica (regla de negocio 3.8.1).
    """
    return []


def editar(db: Session, id_consulta: str, data: ConsultaUpdate):
    """
    Edita una consulta existente.
    Regla de negocio 6.6: al editar se marca el campo 'editado = True'
    y se registra la fecha de edicion. Esto queda visible para el tutor.
    """
    pass
