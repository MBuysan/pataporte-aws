from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session
import jwt
from jwt import PyJWTError
import os
from config.database import get_db
from schemas.consulta import ConsultaCreate, ConsultaResponse
from services import historial_service, consulta_service

from utils import password_utils

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM", "HS256")

def get_current_vet(token: str = Depends(password_utils.oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

    except PyJWTError:
        raise HTTPException(
            status_code=401,
            detail="No autorizado"
        )
    id_veterinario = payload.get("sub")

    if not id_veterinario:
        raise HTTPException(status_code=401, detail="Token inválido")

    return id_veterinario

router = APIRouter(    dependencies=[Depends(get_current_vet)])

@router.post(
    "/consultas",
    response_model=ConsultaResponse,
    status_code=201,
    summary="Agregar consulta al historial de una mascota",
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


