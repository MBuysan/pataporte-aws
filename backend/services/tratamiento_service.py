import uuid
from datetime import datetime
from sqlalchemy.orm import Session
from fastapi import HTTPException

from schemas.tratamiento import TratamientoCreate, TratamientoUpdate
from config.database import Tratamiento, Mascota


def crear(db: Session, data: TratamientoCreate) -> Tratamiento:
    """Registra un nuevo tratamiento para una mascota."""
    mascota = db.query(Mascota).filter(
        Mascota.id_mascota == data.id_mascota,
        Mascota.estado     == "activo"
    ).first()
    if not mascota:
        raise HTTPException(status_code=404, detail="Mascota no encontrada o inactiva")
 
    tratamiento = Tratamiento(
        id_mascota   = data.id_mascota,
        nombre       = data.nombre,
        descripcion  = data.descripcion,
        finalizacion = data.finalizacion,
    )
    db.add(tratamiento)
    db.commit()
    db.refresh(tratamiento)
    return tratamiento



def editar_tratamiento(db: Session, data: TratamientoCreate) -> Tratamiento:
    """
    Registra un nuevo tratamiento para una mascota.
    Verifica que la mascota exista y esté activa.
    Regla: no puede haber dos tratamientos con el mismo nombre para la misma mascota.
    """
    mascota = db.query(Mascota).filter(
        Mascota.id_mascota == data.id_mascota,
        Mascota.estado     == "activo"
    ).first()
    if not mascota:
        raise HTTPException(status_code=404, detail="Mascota no encontrada o inactiva")
 
    tratamiento = Tratamiento(
        id_mascota   = data.id_mascota,
        nombre       = data.nombre,
        descripcion  = data.descripcion,
        finalizacion = data.finalizacion,
    )
    db.add(tratamiento)
    db.commit()
    db.refresh(tratamiento)
    return tratamiento


def ver_tratamientos_activos(db: Session, id_mascota: str) -> list[Tratamiento]:
    """
    Retorna los tratamientos activos (sin fecha de finalización o con fecha futura)
    de una mascota, ordenados del más reciente al más antiguo.
    """
    mascota = db.query(Mascota).filter(Mascota.id_mascota == id_mascota).first()
    if not mascota:
        raise HTTPException(status_code=404, detail="Mascota no encontrada")
 
    return (
        db.query(Tratamiento)
        .filter(
            Tratamiento.id_mascota == id_mascota,
            (Tratamiento.finalizacion == None) |
            (Tratamiento.finalizacion > datetime.utcnow())
        )
        .order_by(Tratamiento.creacion.desc())
        .all()
    )


def listar_por_mascota(db: Session, id_mascota: str) -> list[Tratamiento]:
    """
    Retorna todos los tratamientos (activos e históricos) de una mascota.
    """
    mascota = db.query(Mascota).filter(Mascota.id_mascota == id_mascota).first()
    if not mascota:
        raise HTTPException(status_code=404, detail="Mascota no encontrada")
 
    return (
        db.query(Tratamiento)
        .filter(Tratamiento.id_mascota == id_mascota)
        .order_by(Tratamiento.creacion.desc())
        .all()
    )


def obtener_por_id(db: Session, id_tratamiento: str) -> Tratamiento:
    """Busca un tratamiento por UUID."""
    tratamiento = db.query(Tratamiento).filter(
        Tratamiento.id_tratamiento == id_tratamiento
    ).first()
    if not tratamiento:
        raise HTTPException(status_code=404, detail="Tratamiento no encontrado")
    return tratamiento

