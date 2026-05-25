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
from schemas.verificacion_email import VerificarEmailRequest, ReenviarVerificacionRequest
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


@router.post("/login/veterinario", response_model=VeterinariaLoginResponse, summary="Iniciar sesión de organización/veterinario")
def login_veterinaria_endpoint(data: LoginRequest, db: Session = Depends(get_db)):
    return auth_service.login_veterinaria(db, data.identificador, data.password)


@router.post(
    "/verificar-email",
    summary="Verifica el email del usuario y realiza auto-login"
)
def verificar_email_endpoint(data: VerificarEmailRequest, db: Session = Depends(get_db)):
    """
    Recibe el código de 6 dígitos, activa la cuenta y retorna el token de sesión.
    """
    return auth_service.verificar_codigo_email(db, data)


@router.post(
    "/reenviar-verificacion",
    response_model=MensajeResponse,
    summary="Reenvía el código de verificación por email"
)
def reenviar_verificacion_endpoint(data: ReenviarVerificacionRequest, db: Session = Depends(get_db)):
    """
    Genera y envía un nuevo código de activación de 6 dígitos.
    """
    auth_service.generar_y_enviar_codigo_verificacion(db, data.email, data.tipo_usuario)
    return {"mensaje": "Si el correo está registrado, se ha enviado un nuevo código de verificación"}

