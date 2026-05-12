from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from schemas.auth import VeterinariaLoginResponse

from config.database import get_db
from schemas.recuperacion_password import (
    SolicitarRecuperacionRequest,
    ResetPasswordRequest,
    MensajeResponse,
)
from schemas.auth import LoginRequest, LoginResponse
from services import auth_service

router = APIRouter()


@router.post(
    "/recuperar",
    response_model=MensajeResponse,
    summary="usuario ingresa su email para iniciar la recuperación.",
)
def solicitar_recuperacion(
    data: SolicitarRecuperacionRequest,  # pydantic valida el body del request automaticamente
    db: Session = Depends(
        get_db
    ),  # Depends(get_db) le pide a FastAPI que inyecte la sesion de BD
):
    return auth_service.solicitar_recuperacion(db, data)


@router.post(
    "/reset", response_model=MensajeResponse, summary="Resetear contraseña con código"
)
def resetear_password(
    data: ResetPasswordRequest,
    db: Session = Depends(get_db),
):
    return auth_service.resetear_password(db, data)


@router.post("/login", response_model=LoginResponse, summary="Iniciar sesión de tutor")
def login(data: LoginRequest, db: Session = Depends(get_db)):
    return auth_service.login_tutor(db, data.identificador, data.password)


@router.post("/login/veterinaria", response_model=VeterinariaLoginResponse, summary="Iniciar sesión de organización/veterinaria")
def login_veterinaria_endpoint(data: LoginRequest, db: Session = Depends(get_db)):
    return auth_service.login_veterinaria(db, data.identificador, data.password)
