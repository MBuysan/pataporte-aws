from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session

from config.database import get_db
from schemas.vacuna import DosisCreate, DosisResponse, EsquemaVacunacionResponse
from services import vacuna_service

router = APIRouter()

@router.get(
    "/mascota/{id_mascota}",
    summary="Obtener carnet de vacunas de una mascota"
)
def obtener_carnet(
    id_mascota: str,
    db: Session = Depends(get_db),
):

    esquemas = vacuna_service.esquema_por_mascota(db, id_mascota)

    if not esquemas:
        vacuna_service.crear_esquema(db, id_mascota)
        esquemas = vacuna_service.esquema_por_mascota(db, id_mascota)

    return esquemas

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
    db: Session = Depends(get_db),
):
    return vacuna_service.crear_esquema(db, id_mascota)

@router.post(
    "/{id_esquema}/vacunas/{id_vacuna}",
    status_code=201,
    summary="Agregar vacuna a un esquema",
)
def agregar_vacuna_a_esquema(
    id_esquema: str,
    id_vacuna: str,
    db: Session = Depends(get_db),
):
    return vacuna_service.agregar_vacuna_a_esquema(
        db, id_esquema, id_vacuna
    )

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
    return vacuna_service.registrar_dosis(
        db=db,
        data=data,
        id_veterinaria=id_veterinaria
    )

@router.get(
    "/{id_mascota}/carnet",
    response_model=list[EsquemaVacunacionResponse],
    summary="Ver carnet de vacunas de una mascota",
)
def ver_carnet_vacunas(id_mascota: str, db: Session = Depends(get_db)):
    return vacuna_service.esquema_por_mascota(db, id_mascota)