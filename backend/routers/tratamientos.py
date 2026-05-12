from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from config.database import get_db
from schemas.tratamiento import (
    TratamientoCreate,
    TratamientoUpdate,
    TratamientoResponse,
)
from services import tratamiento_service

router = APIRouter()


@router.post(
    "/",
    response_model=TratamientoResponse,
    status_code=201,
    summary="Crear tratamiento para una mascota",
)
def crear_tratamiento(data: TratamientoCreate, db: Session = Depends(get_db)):
    return tratamiento_service.crear(db, data)


@router.get(
    "/{id_mascota}/activos",
    response_model=list[TratamientoResponse],
    summary="Ver tratamientos activos de una mascota",
)
def ver_tratamientos_activos(id_mascota: str, db: Session = Depends(get_db)):
    return tratamiento_service.ver_tratamientos_activos(db, id_mascota)


@router.get(
    "/{id_mascota}",
    response_model=list[TratamientoResponse],
    summary="Listar todos los tratamientos de una mascota",
)
def listar_tratamientos(id_mascota: str, db: Session = Depends(get_db)):
    return tratamiento_service.listar_por_mascota(db, id_mascota)


@router.patch(
    "/{id_tratamiento}",
    response_model=TratamientoResponse,
    summary="Editar un tratamiento existente",
    description="Modifica nombre, descripción o fecha de finalización. "
)
def actualizar_tratamiento(
    id_tratamiento: str,
    data: TratamientoUpdate,
    db: Session = Depends(get_db),
):
    return tratamiento_service.actualizar(db, id_tratamiento, data)


@router.patch(
    "/{id_tratamiento}/finalizar",
    response_model=TratamientoResponse,
    summary="Marcar un tratamiento como finalizado",
)
def finalizar_tratamiento(
    id_tratamiento: str,
    db: Session = Depends(get_db),
):
    data = TratamientoUpdate(finalizacion=datetime.utcnow())
    return tratamiento_service.actualizar(db, id_tratamiento, data)