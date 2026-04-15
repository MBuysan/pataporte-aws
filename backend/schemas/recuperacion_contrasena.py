import re
from pydantic import BaseModel, EmailStr, field_validator


#  lo que se recibe al solicitar recuperacion
class SolicitarRecuperacionRequest(BaseModel):
    email: EmailStr

    class Config:
        json_schema_extra = {
            "example": {
                "email": "juan@email.com"
            }
        }


#  Lo que se recibe al resetear la contraseña
class ResetPasswordRequest(BaseModel):
    codigo:             str   # el codigo de 6 caracteres que llego al email
    nueva_password:     str
    confirmar_password: str

    # @field_validator es un decorador: le dice a Pydantic que ejecute
    # esta funcion cada vez que llegue el campo "nueva_password"
    # Si lanza ValueError, Pydantic lo convierte en error HTTP 422 automaticamente
    @field_validator("nueva_password")
    @classmethod
    def validar_password_fuerte(cls, v: str) -> str:
        validar_password(v)
        return v  # si paso todas las validaciones, devuelve el valor sin cambios

    @field_validator("confirmar_password")
    @classmethod
    def passwords_coinciden(cls, v: str, info) -> str:
        # info.data contiene los campos ya validados antes que este
        # solo comparamos si nueva_password ya paso su validacion
        if "nueva_password" in info.data and v != info.data["nueva_password"]:
            raise ValueError("Las contraseñas no coinciden")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "codigo":             "A1B2C3",
                "nueva_password":     "NuevaClave1!",
                "confirmar_password": "NuevaClave1!"
            }
        }


# lo que se devuelve en ambos endpoints 
class MensajeResponse(BaseModel):
    mensaje: str