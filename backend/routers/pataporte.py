from utils.auth import get_current_user, get_current_vet, get_current_tutor, require_tutor, require_pet_access
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from config.database import get_db
from services import pataporte_service
from utils import password_utils


router = APIRouter()


@router.post(
    "/{id_mascota}",
    status_code=201,
    summary="Generar pataporte de una mascota",
    description=(
        "Genera un nuevo Pataporte (credencial W3C VC) con el estado actual de vacunación. "
        "Si ya existe uno vigente, pasa a estado 'deprecado'."
        "Requiere autenticación de veterinario o tutor asociado a la mascota."
        "El PDF del pataporte se envía por email al tutor registrado."
    ),
)
def generar_pataporte(
    id_mascota: str,
    db: Session = Depends(get_db),
    usuario: dict = Depends(get_current_user),
):
    require_pet_access(db, id_mascota, usuario)
    pataporte = pataporte_service.generar_pataporte(db = db, id_mascota = id_mascota, emitido_por_rol = usuario["rol"], emitido_por_id = usuario["id"])
    return {
        "id_pataporte":      pataporte.id_pataporte,
        "hash_verificacion": pataporte.hash_verificacion,
        "estado":            pataporte.estado,
        "fecha_emision":     pataporte.fecha_emision.isoformat(),
        "mensaje":           "Pataporte generado; envío por correo solicitado."
    }


@router.get(
    "/verificar/{hash_verificacion}",
    summary="Verificar autenticidad de un pataporte",
    description=(
        "Dado el hash impreso en el PDF, devuelve el estado "
        "y los datos del pataporte. Requiere autenticación y acceso a la mascota."
    ),
)
def verificar_pataporte(hash_verificacion: str, db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    from config.database import Pataporte
    record = db.query(Pataporte).filter_by(hash_verificacion=hash_verificacion).first()
    if not record:
        raise HTTPException(status_code=404, detail="Pataporte no encontrado")
    require_pet_access(db, record.id_mascota, user)
    return pataporte_service.verificar_pataporte(db, hash_verificacion)