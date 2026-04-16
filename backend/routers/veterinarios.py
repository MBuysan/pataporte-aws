from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from config.database import get_db, Veterinaria

router = APIRouter()


@router.get(
    "/",
    summary="Listar veterinarios"
    )
def listar_veterinarios(
    db: Session = Depends(get_db)
    ):
    return db.query(Veterinaria).filter(Veterinaria.estado == "activo").all()


@router.get(
    "/{id_veterinario}",
    summary="Obtener veterinario"
    )
def obtener_veterinario(
    id_veterinario: str,
    db: Session = Depends(get_db)
    ):
    vet = db.query(Veterinaria).filter(Veterinaria.id_veterinaria == id_veterinario).first()
    if not vet:
        raise HTTPException(status_code=404, detail="Veterinario no encontrado")
    return vet
