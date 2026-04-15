from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from config.database import get_db
from schemas.recuperacion import SolicitarRecuperacionRequest, ResetPasswordRequest, MensajeResponse
from services import auth_service

# en main.py se registra con un prefix="/auth", para que todas las
# rutas definidas aca quedan bajo /auth/
router = APIRouter()

@router.post(
    "/recuperar",
    response_model=MensajeResponse,     # define la forma del JSON que devuelve
    summary="Solicitar recuperación de contraseña",
    description="""
paso 1: el usuario ingresa su email para iniciar la recuperación.

- si el email está registrado, se genera un código de 6 caracteres y se envía al correo.
- el código expira en 15 minutos.
- si el email no está registrado, la respuesta es la misma (por seguridad no se revela si existe o no).
""",
)
def solicitar_recuperacion(
    data: SolicitarRecuperacionRequest,  # pydantic valida el body del request automaticamente
    db: Session = Depends(get_db),       # Depends(get_db) le pide a FastAPI que inyecte la sesion de BD 
):                                       
    return auth_service.solicitar_recuperacion(db, data)


@router.post(
    "/reset",
    response_model=MensajeResponse,
    summary="Resetear contraseña con código",
    description="""
paso 2: el usuario ingresa el código recibido y su nueva contraseña.

Requisitos de la nueva contraseña:
- mínimo 6 caracteres
- al menos una mayúscula
- al menos una minúscula
- al menos un número
- al menos un carácter especial (!@#$%)
- debe ser diferente a la contraseña anterior
""",
)
def resetear_password(
    data: ResetPasswordRequest,
    db: Session = Depends(get_db),
):
    return auth_service.resetear_password(db, data)