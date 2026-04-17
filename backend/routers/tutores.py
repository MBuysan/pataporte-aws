from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from config.database import get_db
from schemas.tutor import TutorCreate, TutorUpdate, TutorResponse
from schemas.mascota import MascotaResponse
from services import tutor_service

router = APIRouter()


@router.post("/", response_model=TutorResponse, status_code=201, summary="Registrar tutor")
def registrar_tutor(data: TutorCreate, db: Session = Depends(get_db)):

    try:
        return tutor_service.crear_tutor(db, data)

    except ValueError as e:
        if str(e) == "CEDULA_EXISTE":
            raise HTTPException(status_code=400, detail="Cédula ya registrada")

        if str(e) == "EMAIL_EXISTE":
            raise HTTPException(status_code=400, detail="Email ya registrado")

        raise HTTPException(status_code=500, detail="Error interno")

@router.get("/{id_tutor}", response_model=TutorResponse, summary="Obtener tutor")
def obtener_tutor(id_tutor: str, db: Session = Depends(get_db)):
    tutor = tutor_service.obtener_por_id(db, id_tutor)
    if not tutor:
        raise HTTPException(status_code=404, detail="Tutor no encontrado")
    return tutor


@router.patch("/{id_tutor}", response_model=TutorResponse, summary="Actualizar tutor")
def actualizar_tutor(id_tutor: str, data: TutorUpdate, db: Session = Depends(get_db)):
    return tutor_service.actualizar(db, id_tutor, data)


@router.get("/{id_tutor}/mascotas", response_model=list[MascotaResponse], summary="Mascotas del tutor")
def mascotas_del_tutor(id_tutor: str, db: Session = Depends(get_db)):
    return tutor_service.obtener_mascotas(db, id_tutor)
