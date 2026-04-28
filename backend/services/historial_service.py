from datetime import datetime
from sqlalchemy.orm import Session
from fastapi import HTTPException

from schemas.consulta import ConsultaCreate
from config.database import Consulta, Mascota
from services import consulta_service

def agregar_consulta_al_historial(
    db: Session, data: ConsultaCreate, id_veterinario: str
) -> Consulta:
    """
    Registra una consulta clínica en el historial de la mascota.
    El id_veterinario proviene del token JWT (no del body).
    La fecha_hora la asigna el sistema automáticamente.
    Regla de negocio 3.8.1: el historial pertenece a la mascota.
    """
    return consulta_service.crear(db, data, id_veterinario)


def ver_historial_consultas(db: Session, id_mascota: str) -> list[Consulta]:
    """
    Retorna todas las consultas de una mascota, ordenadas de más reciente a más antigua.
    Regla de negocio 3.8.1: el historial pertenece a la mascota, no a la clínica.
    """
    #verifica si la mascota existe
    mascota = db.query(Mascota).filter(Mascota.id_mascota == id_mascota).first()
    if not mascota:
        raise HTTPException(status_code=404, detail="Mascota no encontrada")
 
    return (
        db.query(Consulta)
        .filter(Consulta.id_mascota == id_mascota)
        .order_by(Consulta.fecha_hora.desc()) 
        .all()
    )

