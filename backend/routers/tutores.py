from utils.auth import require_own_tutor
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from config.database import get_db
from schemas.tutor import TutorCreate, TutorUpdate, TutorResponse
from schemas.mascota import MascotaResponse, VincularMascotaRequest
from services import tutor_service

router = APIRouter()


@router.post("/{id_tutor}/vincular-mascota", dependencies=[Depends(require_own_tutor)], summary="Vincular mascota con código")
def vincular_mascota(
    id_tutor: str, data: VincularMascotaRequest, db: Session = Depends(get_db)
):
    return tutor_service.vincular_mascota_con_codigo(db, id_tutor, data.codigo)


@router.post(
    "/", response_model=TutorResponse, status_code=201, summary="Registrar tutor"
)
def registrar_tutor(data: TutorCreate, db: Session = Depends(get_db)):

    try:
        return tutor_service.crear(db, data)

    except ValueError as e:
        if str(e) == "CEDULA_EXISTE":
            raise HTTPException(status_code=400, detail="Cédula ya registrada")

        if str(e) == "EMAIL_EXISTE":
            raise HTTPException(status_code=400, detail="Email ya registrado")

        raise HTTPException(status_code=500, detail="Error interno")


@router.get("/{id_tutor}", dependencies=[Depends(require_own_tutor)], response_model=TutorResponse, summary="Obtener tutor")
def obtener_tutor(id_tutor: str, db: Session = Depends(get_db)):
    tutor = tutor_service.obtener_por_id(db, id_tutor)
    if not tutor:
        raise HTTPException(status_code=404, detail="Tutor no encontrado")
    return tutor


@router.patch("/{id_tutor}", dependencies=[Depends(require_own_tutor)], response_model=TutorResponse, summary="Actualizar tutor")
def actualizar_tutor(id_tutor: str, data: TutorUpdate, db: Session = Depends(get_db)):
    return tutor_service.actualizar(db, id_tutor, data)


@router.get(
    "/{id_tutor}/mascotas",
    dependencies=[Depends(require_own_tutor)],
    response_model=list[MascotaResponse],
    summary="Mascotas del tutor",
)
def mascotas_del_tutor(id_tutor: str, db: Session = Depends(get_db)):
    return tutor_service.obtener_mascotas(db, id_tutor)

@router.delete(
    "/{id_tutor}",
    dependencies=[Depends(require_own_tutor)],
    status_code=204,
    summary="Eliminar tutor"
)
def eliminar_tutor(
    id_tutor: str,
    db: Session = Depends(get_db)
):
    tutor_service.eliminar_tutor(
        db,
        id_tutor
    )