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
    summary="Agregar tratamiento a una mascota",
)
def editar_tratamiento(data: TratamientoCreate, db: Session = Depends(get_db)):
    return tratamiento_service.editar_tratamiento(db, data)


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


