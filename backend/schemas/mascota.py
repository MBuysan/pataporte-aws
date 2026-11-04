from pydantic import BaseModel, field_serializer
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

class EspecieEnum(str, Enum):
    perro = "perro"
    gato = "gato"
    otro = "otro"

# ── Lo que se recibe al CREAR una mascota ──────────────────
class MascotaCreate(BaseModel):
    id_tutor: str
    nombre: str
    especie: EspecieEnum
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




# ── Lo que se devuelve al consultar una mascota ────────────
class MascotaResponse(BaseModel):
    id_mascota: str
    nombre: str
    especie: EspecieEnum
    raza: Optional[str]
    fecha_de_nacimiento: Optional[date]
    sexo: SexoEnum
    foto_url: Optional[str]
    fecha_registro: datetime
    estado: EstadoEnum

    @field_serializer("foto_url")
    def serialize_photo(self, value):
        from config.storage import photo_url
        return photo_url(value)

    class Config:
        from_attributes = True  # permite convertir objetos SQLAlchemy a este schema


class CodigoAccesoResponse(BaseModel):
    codigo: str
    fecha_expiracion: datetime

    class Config:
        from_attributes = True


class VincularMascotaRequest(BaseModel):
    codigo: str



class ResultadoBusquedaTutor(BaseModel):
    
    """
    esquema resultado de busqueda del tutor y sus mascotas por parte del veterinario,
    agrupa nombre de tutor y un resumen de info de cada mascota
    
    """
    
    nombre_tutor: str
    mascotas:     list["MascotaResumen"]
 
    class Config:
        from_attributes = True
        
        
        
class MascotaResumen(BaseModel):
    
    """
    esquema resumen de mascotas 
    mediante la cédula de un tutor se accede a los siguientes atributos de las mascotas
    
    la edad es calculada
    """
    
    id_mascota: str
    nombre:     str
    especie:    EspecieEnum
    foto_url:   Optional[str]
    edad:       Optional[int]

    @field_serializer("foto_url")
    def serialize_photo(self, value):
        from config.storage import photo_url
        return photo_url(value)
 
    class Config:
        from_attributes = True
