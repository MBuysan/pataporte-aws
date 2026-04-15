from pydantic import BaseModel, EmailStr, field_validator
from datetime import datetime
from typing import Optional



# ── Lo que se recibe al REGISTRAR un tutor ─────────────────
class TutorCreate(BaseModel):
    nombre: str
    cedula: str
    email: EmailStr  # Pydantic valida automaticamente que sea un email valido
    password: str
    telefono: Optional[str] = None

    @field_validator("cedula") # hay que agregar el api que valida el numero de cedula
    @classmethod
    def cedula_no_vacia(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("La cedula no puede estar vacia")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "nombre": "Juan Perez",
                "cedula": "12345678",
                "email": "juan@email.com",
                "password": "123456",
                "telefono": "099123456"
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
