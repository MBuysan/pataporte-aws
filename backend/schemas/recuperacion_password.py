from pydantic import BaseModel, EmailStr, field_validator
from utils.password_utils import validar_password


#  lo que se recibe al solicitar recuperacion
class SolicitarRecuperacionRequest(BaseModel):
    email: EmailStr

    class Config:
        json_schema_extra = {"example": {"email": "juan@email.com"}}


#  Lo que se recibe al resetear la contraseña
class ResetPasswordRequest(BaseModel):
    codigo: str  # el codigo/token de 6 caracteres que llego al email
    nueva_password: str
    confirmar_password: str

    @field_validator("nueva_password")
    @classmethod
    def validar_password_fuerte(
        cls, v: str
    ) -> (
        str
    ):  # cls corresponde a la clase en la que estamos (schema) y v al valor marcado por @field_validator()
        validar_password(v)
        return v

    @field_validator("confirmar_password")
    @classmethod
    def passwords_coinciden(cls, v: str, info) -> str:
        if "nueva_password" in info.data and v != info.data["nueva_password"]:
            raise ValueError("Las contraseñas no coinciden")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "codigo": "A1B2C3",
                "nueva_password": "NuevaClave1!",
                "confirmar_password": "NuevaClave1!",
            }
        }


# lo que se devuelve en ambos endpoints
class MensajeResponse(BaseModel):
    mensaje: str
