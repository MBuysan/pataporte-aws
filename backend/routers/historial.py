from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from config.database import get_db
from schemas.consulta import ConsultaCreate, ConsultaResponse
from services import historial_service, consulta_service

from utils.auth import get_current_vet

router = APIRouter( )

@router.post(
    "/consultas",
    response_model=ConsultaResponse,
    status_code=201,
    summary="Agregar consulta al historial de una mascota",
    dependencies=[Depends(get_current_vet)],
)
def agregar_consulta(
    data: ConsultaCreate,
    db: Session = Depends(get_db),
    id_veterinario: str = Depends(get_current_vet)):
    return consulta_service.crear(db, data, id_veterinario)


@router.get(
    "/{id_mascota}/detalle/{id_consulta}",
    response_model=ConsultaResponse,
    summary="Ver detalle completo de una consulta",
    description="Devuelve la consulta con sus tratamientos y dosis asociadas.",
)
def obtener_detalle_consulta(id_mascota: str, id_consulta: str, db: Session = Depends(get_db)):
    return consulta_service.obtener_detalle(db, id_consulta)
 


@router.get(
    "/{id_mascota}/consultas",
    response_model=list[ConsultaResponse],
    summary="Ver consultas del historial de una mascota",
)
def ver_historial_consultas(id_mascota: str, db: Session = Depends(get_db)):
    return historial_service.ver_historial_consultas(db, id_mascota)

@router.get(
    "/{id_mascota}/unificado",
    summary="Ver historial unificado (consultas, tratamientos y vacunas)"
)
def ver_historial_unificado(id_mascota: str, db: Session = Depends(get_db)):
    return {"eventos": historial_service.obtener_historial_unificado(db, id_mascota)}


