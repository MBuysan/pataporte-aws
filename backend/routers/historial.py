from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from config.database import get_db
from schemas.consulta import ConsultaResponse
from schemas.historial import AgregarConsultaHistorialCreate, HistorialResponse
from services import historial_service

router = APIRouter()


# TODO: reemplazar por dependencia real de autenticación JWT
def _get_id_veterinario(x_veterinario_id: str = Header(...)) -> str:
    """
    Dependencia temporal: el id del veterinario se pasa en el header X-Veterinario-Id.
    En producción debe extraerse del token JWT.
    """
    return x_veterinario_id


@router.post(
    "/consultas",
    response_model=ConsultaResponse,
    status_code=201,
    summary="Agregar consulta al historial",
)
def agregar_consulta_al_historial(
    data: AgregarConsultaHistorialCreate,
    db: Session = Depends(get_db),
    id_veterinario: str = Depends(_get_id_veterinario),
):
    return historial_service.agregar_consulta_al_historial(db, data, id_veterinario)


@router.get(
    "/{id_mascota}",
    response_model=HistorialResponse,
    summary="Visualizar historial completo de una mascota",
)
def visualizar_historial(id_mascota: str, db: Session = Depends(get_db)):
    return historial_service.visualizar_historial(db, id_mascota)


@router.get(
    "/{id_mascota}/consultas",
    response_model=list[ConsultaResponse],
    summary="Ver consultas del historial de una mascota",
)
def ver_historial_consultas(id_mascota: str, db: Session = Depends(get_db)):
    return historial_service.ver_historial_consultas(db, id_mascota)
