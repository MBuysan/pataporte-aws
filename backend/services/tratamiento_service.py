import uuid
from datetime import datetime
from sqlalchemy.orm import Session
from fastapi import HTTPException

from schemas.tratamiento import TratamientoCreate, TratamientoUpdate
from config.database import Tratamiento, Mascota

 
def crear_tratamiento(db: Session,data: TratamientoCreate,id_consulta: str) -> Tratamiento:
    """
    Crea un nuevo tratamiento asociado a una consulta.
    """

    mascota = (
        db.query(Mascota)
        .filter(
            Mascota.id_mascota == data.id_mascota,
            Mascota.estado == "activo"
        )
        .first()
    )

    if not mascota:
        raise HTTPException(
            status_code=404,
            detail="Mascota no encontrada o inactiva"
        )

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

    tratamiento = Tratamiento(
        id_mascota=data.id_mascota,
        nombre=data.nombre,
        descripcion=data.descripcion,
        finalizacion=data.finalizacion,
        id_consulta_creacion=id_consulta,
        id_consulta_ultima_edicion=id_consulta,
    )

    db.add(tratamiento)
    db.commit()
    db.refresh(tratamiento)

    return tratamiento


def ver_tratamientos_activos(db: Session, id_mascota: str) -> list[Tratamiento]:

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

    tratamiento = (
        db.query(Tratamiento)
        .filter(Tratamiento.id_tratamiento == id_tratamiento)
        .first()
    )

    if not tratamiento:
        raise HTTPException(status_code=404, detail="Tratamiento no encontrado")

    return tratamiento


def actualizar_tratamiento(db: Session, id_tratamiento: str, data: TratamientoUpdate, id_consulta: str ) -> Tratamiento:

    tratamiento = obtener_por_id(db, id_tratamiento)

    if (data.nombre is not None and data.nombre != tratamiento.nombre):

        colision = (
            db.query(Tratamiento)
            .filter(
                Tratamiento.id_mascota == tratamiento.id_mascota,
                Tratamiento.nombre == data.nombre,
                Tratamiento.id_tratamiento != id_tratamiento
            )
            .first()
        )

        if colision:
            raise HTTPException(
                status_code=409,
                detail="Ya existe un tratamiento con ese nombre para esta mascota"
            )

        tratamiento.nombre = data.nombre

    if data.descripcion is not None:
        tratamiento.descripcion = data.descripcion

    if data.finalizacion is not None:
        tratamiento.finalizacion = data.finalizacion

    # solo se actualiza la ultima edicion
    tratamiento.id_consulta_ultima_edicion = id_consulta

    db.commit()
    db.refresh(tratamiento)

    return tratamiento