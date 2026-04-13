from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from config.database import get_db
from schemas.vacuna import DosisCreate, DosisResponse, EsquemaVacunacionResponse
from services import vacuna_service

router = APIRouter()

# TODO: reemplazar por dependencia real de autenticación JWT
def _get_id_veterinaria(x_veterinaria_id: str = Header(...)) -> str:
    """
    Dependencia temporal: el id de la veterinaria se pasa en el header X-Veterinaria-Id.
    En producción debe extraerse del token JWT.
    """
    return x_veterinaria_id


@router.post(
    "/crear-carnet/{id_mascota}",
    response_model=EsquemaVacunacionResponse,
    status_code=201,
    summary="Crear carnet de vacunas (esquema) para una mascota",
)
def crear_carnet_vacunas(
    id_mascota: str,
    id_vacuna: str,
    db: Session = Depends(get_db),
):
    return vacuna_service.crear_carnet_vacunas(db, id_mascota, id_vacuna)


@router.post(
    "/dosis",
    response_model=DosisResponse,
    status_code=201,
    summary="Registrar aplicación de una dosis",
)
def agregar_dosis(
    data: DosisCreate,
    db: Session = Depends(get_db),
    id_veterinaria: str = Depends(_get_id_veterinaria),
):
    return vacuna_service.agregar_dosis(db, data, id_veterinaria)


@router.get(
    "/{id_mascota}/carnet",
    response_model=list[EsquemaVacunacionResponse],
    summary="Ver carnet de vacunas de una mascota",
)
def ver_carnet_vacunas(id_mascota: str, db: Session = Depends(get_db)):
    return vacuna_service.ver_carnet_vacunas(db, id_mascota)
