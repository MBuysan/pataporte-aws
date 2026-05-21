from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from config.database import get_db
from schemas.mascota import (
    MascotaCreate,
    MascotaUpdate,
    MascotaResponse,
    CodigoAccesoResponse,
)
from services import mascota_service
from utils import password_utils
import jwt
from jwt import PyJWTError
import os


# todos las etiquetas get,post etc de mas abajo se registran sobre este objeto
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
"""
parametros dentro del endpoint
1er parametro: permite agregar entre llaves un parametro de ruta, usualmente es usado mas adelante en el flujo
2do parametro: le dice lo que espera del retorno, puede ser una forma de objeto especifica del schema, o una lista de los mismos
3er parametro: summary (resumen) o description usualmente
"""
def get_current_tutor(token: str = Depends(password_utils.oauth2_scheme)):
    print("TOKEN RAW:", token)
    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )

    except PyJWTError:

        raise HTTPException(
            status_code=401,
            detail="No autorizado"
        )

    id_tutor = payload.get("sub")

    if not id_tutor:

        raise HTTPException(
            status_code=401,
            detail="Token inválido"
        )

    return id_tutor

router = APIRouter(    dependencies=[Depends(get_current_tutor)])

@router.get(
    "/", response_model=list[MascotaResponse], summary="Listar todas las mascotas"
)
def listar_mascotas(db: Session = Depends(get_db)):
    return mascota_service.listar(db)


@router.get("/{id_mascota}", response_model=MascotaResponse, summary="Obtener mascota")
def obtener_mascota(id_mascota: str, db: Session = Depends(get_db)):
    mascota = mascota_service.obtener_por_id(db, id_mascota)
    if not mascota:
        raise HTTPException(status_code=404, detail="Mascota no encontrada")
    return mascota


@router.post(
    "/", response_model=MascotaResponse, status_code=201, summary="Registrar mascota"
)
def registrar_mascota(data: MascotaCreate, db: Session = Depends(get_db)):
    return mascota_service.crear(db, data)


@router.patch(
    "/{id_mascota}", response_model=MascotaResponse, summary="Actualizar mascota"
)
def actualizar_mascota(
    id_mascota: str, data: MascotaUpdate, db: Session = Depends(get_db)
):
    return mascota_service.actualizar(db, id_mascota, data)


@router.delete("/{id_mascota}", status_code=204, summary="Eliminar mascota")
def eliminar_mascota(
    id_mascota: str,
    db: Session = Depends(get_db),
    id_tutor: str = Depends(get_current_tutor),
):
    mascota_service.eliminar(db, id_mascota, id_tutor)


@router.post(
    "/{id_mascota}/generar-codigo",
    response_model=CodigoAccesoResponse,
    summary="Generar código para compartir",
)
def generar_codigo(id_mascota: str, db: Session = Depends(get_db)):
    return mascota_service.generar_codigo_acceso(db, id_mascota)
