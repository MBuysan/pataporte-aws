from pydantic import BaseModel, EmailStr, field_validator

class VerificarEmailRequest(BaseModel):
    email: EmailStr
    tipo_usuario: str # "tutor" | "veterinario"
    codigo: str

    @field_validator("tipo_usuario")
    @classmethod
    def validar_tipo(cls, v: str) -> str:
        if v not in ["tutor", "veterinario"]:
            raise ValueError("El tipo de usuario debe ser 'tutor' o 'veterinario'")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "email": "usuario@ejemplo.com",
                "tipo_usuario": "tutor",
                "codigo": "X7Y9Z2"
            }
        }

class ReenviarVerificacionRequest(BaseModel):
    email: EmailStr
    tipo_usuario: str # "tutor" | "veterinario"

    @field_validator("tipo_usuario")
    @classmethod
    def validar_tipo(cls, v: str) -> str:
        if v not in ["tutor", "veterinario"]:
            raise ValueError("El tipo de usuario debe ser 'tutor' o 'veterinario'")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "email": "usuario@ejemplo.com",
                "tipo_usuario": "tutor"
            }
        }
