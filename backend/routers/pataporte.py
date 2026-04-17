from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from config.database import get_db
from schemas.pataporte import PataporteResponse, CertificadoVacunasResponse
from services import pataporte_service

router = APIRouter()


@router.get(
    "/{id_mascota}",
    response_model=PataporteResponse,
    summary="Ver pataporte digital de una mascota",
)
def ver_pataporte(id_mascota: str, db: Session = Depends(get_db)):
    return pataporte_service.ver_pataporte(db, id_mascota)


@router.post(
    "/{id_mascota}/generar",
    response_model=PataporteResponse,
    summary="Generar pataporte digital de una mascota",
)
def generar_pataporte(id_mascota: str, db: Session = Depends(get_db)):
    return pataporte_service.generar_pataporte(db, id_mascota)


@router.post(
    "/{id_mascota}/certificado-vacunas",
    response_model=CertificadoVacunasResponse,
    status_code=201,
    summary="Generar certificado de vacunas de una mascota",
)
def generar_certificado_vacunas(id_mascota: str, db: Session = Depends(get_db)):
    return pataporte_service.generar_certificado_vacunas(db, id_mascota)
