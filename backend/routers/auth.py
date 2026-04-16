from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from config.database import get_db
from backend.schemas.recuperacion_password import SolicitarRecuperacionRequest, ResetPasswordRequest, MensajeResponse
from services import auth_service

router = APIRouter()

@router.post(
    "/recuperar",
    response_model=MensajeResponse,    
    summary= "usuario ingresa su email para iniciar la recuperación."
)
def solicitar_recuperacion(
    data: SolicitarRecuperacionRequest,  # pydantic valida el body del request automaticamente
    db: Session = Depends(get_db),       # Depends(get_db) le pide a FastAPI que inyecte la sesion de BD 
):                                       
    return auth_service.solicitar_recuperacion(db, data)


@router.post(
    "/reset",
    response_model=MensajeResponse,
    summary="Resetear contraseña con código"
)
def resetear_password(
    data: ResetPasswordRequest,
    db: Session = Depends(get_db),
):
    return auth_service.resetear_password(db, data)