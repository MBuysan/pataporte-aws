from pydantic import BaseModel
from datetime import date, datetime
from typing import Optional
from enum import Enum

"""
el tipo enum, permite marcar los únicos valores validos para un campo, 
tambien hereda de str para poder manejarse en json y la base de datos
"""


class SexoEnum(str, Enum):
    macho = "macho"
    hembra = "hembra"
    desconocido = "desconocido"


class EstadoEnum(str, Enum):
    activo = "activo"
    inactivo = "inactivo"


# ── Lo que se recibe al CREAR una mascota ──────────────────
class MascotaCreate(BaseModel):
    nombre: str
    especie: str
    raza: Optional[str] = None
    fecha_de_nacimiento: Optional[date] = None
    sexo: SexoEnum = SexoEnum.desconocido
    foto_url: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "nombre": "Firulais",
                "especie": "perro",
                "raza": "Labrador",
                "fecha_de_nacimiento": "2021-03-15",
                "sexo": "macho",
                "foto_url": "https://res.cloudinary.com/pataporte/image/upload/v1234567/mascotas/firulais.jpg",
            }
        }


# ── Lo que se recibe al actualizar una mascota ─────────────
# todos los campos son opcionales: solo se actualizan los que llegan
class MascotaUpdate(BaseModel):
    nombre: Optional[str] = None
    raza: Optional[str] = None
    foto_url: Optional[str] = None


# ── Lo que se devuelve al consultar una mascota ────────────
class MascotaResponse(BaseModel):
    id_mascota: str
    nombre: str
    especie: str
    raza: Optional[str]
    fecha_de_nacimiento: Optional[date]
    sexo: SexoEnum
    foto_url: Optional[str]
    fecha_registro: datetime
    estado: EstadoEnum

    class Config:
        from_attributes = True  # permite convertir objetos SQLAlchemy a este schema


class CodigoAccesoResponse(BaseModel):
    codigo: str
    fecha_expiracion: datetime

    class Config:
        from_attributes = True


class VincularMascotaRequest(BaseModel):
    codigo: str
