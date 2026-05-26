import jwt
import os
from jwt import PyJWTError
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from config.database import get_db
from services import pataporte_service
from utils import password_utils

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM  = os.getenv("ALGORITHM", "HS256")

router = APIRouter()


def get_current_vet(token: str = Depends(password_utils.oauth2_scheme)) -> str:
    """Extrae el id_veterinario del token JWT."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except PyJWTError:
        raise HTTPException(status_code=401, detail="No autorizado")
    id_veterinario = payload.get("sub")
    if not id_veterinario:
        raise HTTPException(status_code=401, detail="Token inválido")
    return id_veterinario


@router.post(
    "/{id_mascota}",
    status_code=201,
    summary="Generar pataporte de una mascota",
    description=(
        "Genera un nuevo Pataporte (credencial W3C VC) con el estado actual de vacunación. "
        "Si ya existe uno vigente, pasa a estado 'deprecado'."
    ),
)
def generar_pataporte(
    id_mascota: str,
    db: Session = Depends(get_db),
    id_veterinario: str = Depends(get_current_vet),
):
    pataporte = pataporte_service.generar_pataporte(db, id_mascota, id_veterinario)
    return {
        "id_pataporte":      pataporte.id_pataporte,
        "hash_verificacion": pataporte.hash_verificacion,
        "estado":            pataporte.estado,
        "fecha_emision":     pataporte.fecha_emision.isoformat(),
    }


@router.get(
    "/verificar/{hash_verificacion}",
    summary="Verificar autenticidad de un pataporte",
    description=(
        "Dado el hash impreso en el PDF, devuelve el estado "
        "y los datos del pataporte. No requiere autenticación."
    ),
)
def verificar_pataporte(hash_verificacion: str, db: Session = Depends(get_db)):
    return pataporte_service.verificar_pataporte(db, hash_verificacion)