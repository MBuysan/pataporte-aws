from utils.auth import get_current_vet
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from config.database import get_db, Veterinario
from schemas.mascota import ResultadoBusquedaTutor
from schemas.veterinario import VeterinarioCreate, VeterinarioResponse
from services import veterinario_service

router = APIRouter()


@router.post(
    "/",
    response_model=VeterinarioResponse,
    status_code=201,
    summary="Registrar un veterinario y su organización",
)
def registrar_veterinario(data: VeterinarioCreate, db: Session = Depends(get_db)):
    return veterinario_service.registrar_veterinario(db, data)



@router.get(dependencies=[Depends(get_current_vet)],
    path="/buscar/{cedula}",
    response_model=ResultadoBusquedaTutor,
    summary="Buscar mascotas por cédula del tutor",
)
def buscar_por_cedula(cedula: str, db: Session = Depends(get_db)):
    return veterinario_service.buscar_por_cedula(db, cedula)


@router.get(dependencies=[Depends(get_current_vet)], path="/", response_model=list[VeterinarioResponse], summary="Listar veterinarios")
def listar_veterinarios(db: Session = Depends(get_db)):
    return db.query(Veterinario).filter(Veterinario.estado == "activo").all()


@router.get(dependencies=[Depends(get_current_vet)], path="/{id_veterinario}", response_model=VeterinarioResponse, summary="Obtener veterinario por id")
def obtener_veterinario(id_veterinario: str, db: Session = Depends(get_db)):
    vet = (
        db.query(Veterinario)
        .filter(Veterinario.id_veterinario == id_veterinario)
        .first()
    )
    if not vet:
        raise HTTPException(status_code=404, detail="Veterinario no encontrado")
    return vet
