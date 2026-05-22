from pydantic import BaseModel, EmailStr, field_validator
from datetime import datetime
from typing import Optional


# ── Lo que se recibe al REGISTRAR un tutor ─────────────────
class TutorCreate(BaseModel):
    nombre: str
    cedula: str
    email: EmailStr  # pydantic valida automaticamente que sea un email valido
    password: str
    telefono: Optional[str] = None

    @field_validator("cedula")
    @classmethod
    def validar_cedula(cls, v: str) -> str:
        cedula = "".join(filter(str.isdigit, v.strip()))

        if len(cedula) < 7 or len(cedula) > 8:
            raise ValueError("La cédula debe tener 7 u 8 números")

        cedula = cedula.zfill(8)

        pesos = [2, 9, 8, 7, 6, 3, 4]
        suma = 0

        for i in range(7):
            suma += int(cedula[i]) * pesos[i]

        digito = (10 - (suma % 10)) % 10

        if digito != int(cedula[7]):
            raise ValueError("La cédula ingresada no es válida")

        return cedula

    class Config:
        json_schema_extra = {
            "example": {
                "nombre": "Juan Perez",
                "cedula": "12345678",
                "email": "juan@email.com",
                "password": "123456",
                "telefono": "099123456",
            }
        }


# ── Lo que se recibe al ACTUALIZAR un tutor ────────────────
class TutorUpdate(BaseModel):
    nombre: Optional[str] = None
    email: Optional[EmailStr] = None
    telefono: Optional[str] = None


# ── Lo que se DEVUELVE al consultar un tutor ───────────────
class TutorResponse(BaseModel):
    id_tutor: str
    nombre: str
    cedula: str
    email: str
    telefono: Optional[str]
    fecha_registro: datetime
    estado: str

    class Config:
        from_attributes = True
