import uuid
from datetime import datetime
from sqlalchemy.orm import Session
from fastapi import HTTPException

from schemas.tratamiento import TratamientoCreate, TratamientoUpdate
from config.database import Tratamiento, Mascota


def agregar_tratamiento(db: Session, data: TratamientoCreate) -> Tratamiento:

    mascota = (
        db.query(Mascota)
        .filter(
            Mascota.id_mascota == data.id_mascota,
            Mascota.estado == "activo"
        )
        .first()
    )

    if not mascota:
        raise HTTPException(status_code=404, detail="Mascota no encontrada o inactiva")

    duplicado = (
        db.query(Tratamiento)
        .filter(
            Tratamiento.id_mascota == data.id_mascota,
            Tratamiento.nombre == data.nombre
        )
        .first()
    )

    if duplicado:
        raise HTTPException(
            status_code=409,
            detail="Ya existe un tratamiento con ese nombre para esta mascota"
        )

    nuevo = Tratamiento(
        id_mascota=data.id_mascota,
        nombre=data.nombre,
        descripcion=data.descripcion,
        finalizacion=data.finalizacion
    )

    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)

    # mock notificación
    print(f"NOTIFICACIÓN: nuevo tratamiento '{nuevo.nombre}' para mascota {data.id_mascota}")

    return nuevo


def ver_tratamientos_activos(db: Session, id_mascota: str) -> list[Tratamiento]:

    mascota = db.query(Mascota).filter(Mascota.id_mascota == id_mascota).first()

    if not mascota:
        raise HTTPException(status_code=404, detail="Mascota no encontrada")

    return (
        db.query(Tratamiento)
        .filter(
            Tratamiento.id_mascota == id_mascota,
            Tratamiento.finalizacion.is_(None)
        )
        .order_by(Tratamiento.creacion.desc())
        .all()
    )


def listar_por_mascota(db: Session, id_mascota: str) -> list[Tratamiento]:

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

    tratamiento = (
        db.query(Tratamiento)
        .filter(Tratamiento.id_tratamiento == id_tratamiento)
        .first()
    )

    if not tratamiento:
        raise HTTPException(status_code=404, detail="Tratamiento no encontrado")

    return tratamiento


def actualizar(db: Session, id_tratamiento: str, data: TratamientoUpdate) -> Tratamiento:

    tratamiento = obtener_por_id(db, id_tratamiento)

    if data.descripcion is not None:
        tratamiento.descripcion = data.descripcion

    if data.finalizacion is not None:
        tratamiento.finalizacion = data.finalizacion

    db.commit()
    db.refresh(tratamiento)

    return tratamiento
