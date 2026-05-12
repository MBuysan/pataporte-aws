from pydantic import BaseModel
from datetime import datetime
from typing import Optional


# ── Lo que se recibe al CREAR un tratamiento ──────────────
class TratamientoCreate(BaseModel):

    nombre: str
    descripcion: Optional[str] = None
    finalizacion: Optional[datetime] = None

    class Config:
        json_schema_extra = {
            "example": {
                "nombre": "Antibiótico 10 días",
                "descripcion": "Amoxicilina 250mg cada 12hs durante 10 días",
                "finalizacion": "2024-06-20T00:00:00",
            }
        }


# ── Lo que se recibe al ACTUALIZAR un tratamiento ─────────
class TratamientoUpdate(BaseModel):
    nombre:       Optional[str]      = None
    descripcion:  Optional[str]      = None
    finalizacion: Optional[datetime] = None


# ── Lo que se DEVUELVE al consultar un tratamiento ────────
class TratamientoResponse(BaseModel):
    id_tratamiento: str
    id_mascota: str
    nombre: str
    descripcion: Optional[str]
    creacion: datetime
    finalizacion: Optional[datetime]
    id_consulta_creacion: str
    id_consulta_ultima_edicion: str

    class Config:
        from_attributes = True
