import uuid
from datetime import datetime
from sqlalchemy.orm import Session
from fastapi import HTTPException

from schemas.historial import AgregarConsultaHistorialCreate
from config.database import Consulta, Tratamiento, Mascota


def agregar_consulta_al_historial(db: Session, data: AgregarConsultaHistorialCreate, id_veterinario: str) -> Consulta:
    """
    Registra una consulta clínica en el historial de la mascota.
    El id_veterinario proviene del token JWT (no del body).
    La fecha_hora la asigna el sistema automáticamente.
    Regla de negocio 3.8.1: el historial pertenece a la mascota.
    """
    pass


def ver_historial_consultas(db: Session, id_mascota: str) -> list[Consulta]:
    """
    Retorna todas las consultas de una mascota, ordenadas de más reciente a más antigua.
    Regla de negocio 3.8.1: el historial pertenece a la mascota, no a la clínica.
    """
    pass

def visualizar_historial(db: Session, id_mascota: str) -> dict:
    """
    Retorna el historial completo de la mascota: datos básicos, consultas y tratamientos.
    """
    pass