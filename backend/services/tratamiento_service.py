import uuid
from datetime import datetime
from sqlalchemy.orm import Session
from fastapi import HTTPException

from schemas.tratamiento import TratamientoCreate, TratamientoUpdate
from config.database import Tratamiento, Mascota, Consulta


def agregar_tratamiento(db: Session, data: TratamientoCreate) -> Tratamiento:
    """
    Registra un nuevo tratamiento para una mascota.
    El tratamiento queda asociado a la consulta que lo originó.
    """

    # El id_consulta es una dependencia de la HU de consultas; KEY-7 solo lo consume.
    consulta = (
        db.query(Consulta)
        .filter(Consulta.id_consulta == data.id_consulta)
        .first()
    )
    if not consulta:
        raise HTTPException(
            status_code=404,
            detail=(
                "Consulta no encontrada. "
                "El id_consulta debe venir de la HU dependiente de consultas."
            ),
        )

    mascota = (
        db.query(Mascota)
        .filter(
            Mascota.id_mascota == consulta.id_mascota,
            Mascota.estado == "activo"
        )
        .first()
    )
    if not mascota:
        raise HTTPException(status_code=404, detail="Mascota no encontrada o inactiva")

    duplicado = (
        db.query(Tratamiento)
        .filter(
            Tratamiento.id_mascota == consulta.id_mascota,
            Tratamiento.nombre == data.nombre
        )
        .first()
    )
    if duplicado:
        raise HTTPException(
            status_code=409,
            detail="Ya existe un tratamiento con ese nombre para esta mascota"
        )

    nuevo_tratamiento = Tratamiento(
        id_mascota=consulta.id_mascota,
        id_consulta=data.id_consulta,
        nombre=data.nombre,
        indicaciones=data.indicaciones,
        fecha_inicio=data.fecha_inicio,
        fecha_fin_estimada=data.fecha_fin_estimada,
        fecha_fin_real=None,
    )

    db.add(nuevo_tratamiento)
    db.commit()
    db.refresh(nuevo_tratamiento)

    # Mock de notificación
    print(f"NOTIFICACIÓN: nuevo tratamiento '{nuevo_tratamiento.nombre}' para la mascota {consulta.id_mascota}")

    return nuevo_tratamiento


def ver_tratamientos_activos(db: Session, id_mascota: str) -> list[Tratamiento]:
    """
    Retorna los tratamientos activos de una mascota.
    Un tratamiento activo es aquel que no tiene fecha_fin_real.
    """
    mascota = (
        db.query(Mascota)
        .filter(Mascota.id_mascota == id_mascota)
        .first()
    )
    if not mascota:
        raise HTTPException(status_code=404, detail="Mascota no encontrada")

    return (
        db.query(Tratamiento)
        .filter(
            Tratamiento.id_mascota == id_mascota,
            Tratamiento.fecha_fin_real.is_(None)
        )
        .order_by(Tratamiento.fecha_inicio.desc())
        .all()
    )


def listar_por_mascota(db: Session, id_mascota: str) -> list[Tratamiento]:
    """
    Retorna todos los tratamientos de una mascota.
    """
    mascota = (
        db.query(Mascota)
        .filter(Mascota.id_mascota == id_mascota)
        .first()
    )
    if not mascota:
        raise HTTPException(status_code=404, detail="Mascota no encontrada")

    return (
        db.query(Tratamiento)
        .filter(Tratamiento.id_mascota == id_mascota)
        .order_by(Tratamiento.fecha_inicio.desc())
        .all()
    )


def obtener_por_id(db: Session, id_tratamiento: str) -> Tratamiento:
    """Busca un tratamiento por UUID."""
    tratamiento = (
        db.query(Tratamiento)
        .filter(Tratamiento.id_tratamiento == id_tratamiento)
        .first()
    )

    if not tratamiento:
        raise HTTPException(status_code=404, detail="Tratamiento no encontrado")

    return tratamiento


def actualizar(
    db: Session, id_tratamiento: str, data: TratamientoUpdate
) -> Tratamiento:
    """Actualiza un tratamiento existente."""

    tratamiento = obtener_por_id(db, id_tratamiento)

    if data.nombre is not None:
        tratamiento.nombre = data.nombre

    if data.indicaciones is not None:
        tratamiento.indicaciones = data.indicaciones

    if data.fecha_inicio is not None:
        tratamiento.fecha_inicio = data.fecha_inicio

    if data.fecha_fin_estimada is not None:
        tratamiento.fecha_fin_estimada = data.fecha_fin_estimada

    if data.fecha_fin_real is not None:
        tratamiento.fecha_fin_real = data.fecha_fin_real

    if (
        tratamiento.fecha_fin_estimada is not None
        and tratamiento.fecha_fin_estimada < tratamiento.fecha_inicio
    ):
        raise HTTPException(
            status_code=400,
            detail="La fecha de fin estimada no puede ser anterior a la fecha de inicio",
        )

    if (
        tratamiento.fecha_fin_real is not None
        and tratamiento.fecha_fin_real < tratamiento.fecha_inicio
    ):
        raise HTTPException(
            status_code=400,
            detail="La fecha de fin real no puede ser anterior a la fecha de inicio",
        )

    db.commit()
    db.refresh(tratamiento)

    return tratamiento
