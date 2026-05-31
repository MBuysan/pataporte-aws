from http.client import HTTPException
import os
import jwt
from jwt import PyJWTError
from utils import password_utils
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from config.database import get_db
from schemas.vacuna import DosisCreate, DosisResponse, EsquemaVacunacionResponse, EditarEsquemaVacuna
from services import vacuna_service
from config.database import Dosis, EsquemaVacunacion, EsquemaVacuna
from typing import Optional

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM  = os.getenv("ALGORITHM", "HS256")

router = APIRouter()

def get_current_vet(token: str = Depends(password_utils.oauth2_scheme)) -> str:
    """Extrae el id_veterinario del token JWT."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except PyJWTError:
        raise HTTPException(status_code=401, detail="No autorizado")
    if payload.get("rol") != "veterinario":
        raise HTTPException(status_code=401, detail="No autorizado")

    id_veterinario = payload.get("sub")
    if not id_veterinario:
        raise HTTPException(status_code=401, detail="Token inválido")
    return id_veterinario

@router.get(
    "/{id_mascota}/carnet",
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
    id_veterinario: str = Depends(get_current_vet),
):
    return vacuna_service.registrar_dosis(
        db=db,
        data=data,
        id_veterinario=id_veterinario
    )

@router.get("/tipos")
def ver_vacunas(
    especie: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    return vacuna_service.obtener_tipos_vacuna(db, especie)

@router.get("/consulta/{id_consulta}")
def vacunas_por_consulta(id_consulta: str, db: Session = Depends(get_db)):

    return (
        db.query(Dosis)
        .filter(Dosis.id_consulta == id_consulta)
        .all()
    )

@router.get("/mascota/{id_mascota}/vacunas")
def vacunas_mascota(id_mascota: str, db: Session = Depends(get_db)):

    return (
        db.query(EsquemaVacuna)
        .join(EsquemaVacunacion)
        .filter(EsquemaVacunacion.id_mascota == id_mascota)
        .all()
    )

@router.put(
    "/editar-esquema-vacuna/{id_esquema_vacuna}",
    summary="Agregar o eliminar dosis"
)
def editar_esquema_vacuna(
    id_esquema_vacuna: str,
    data: EditarEsquemaVacuna,
    db: Session = Depends(get_db),
    id_veterinario: str = Depends(get_current_vet),
):

    return vacuna_service.editar_esquema_vacuna(
        db=db,
        id_esquema_vacuna=id_esquema_vacuna,
        agregar_dosis=data.agregar_dosis,
        eliminar_dosis=data.eliminar_dosis,
        id_veterinario=id_veterinario
    )