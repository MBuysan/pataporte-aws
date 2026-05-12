from pydantic import BaseModel
from datetime import datetime
from typing import Optional


# ── Lo que se recibe al CREAR un tratamiento ──────────────
class TratamientoCreate(BaseModel):

    nombre:      str
    descripcion: Optional[str] = None   # indicaciones / nombre del medicamento
    frecuencia:  Optional[str] = None   # ej: "1 pastilla cada 12hs"
    inicio:      Optional[datetime] = None   # si no se manda, el service usa utcnow()
    finalizacion: Optional[datetime] = None

    class Config:
        json_schema_extra = {
            "example": {
                "nombre":       "Amoxicilina",
                "descripcion":  "Antibiótico para infección urinaria",
                "frecuencia":   "1 comprimido de 250mg cada 12hs",
                "inicio":       "2025-06-01T00:00:00",
                "finalizacion": "2025-06-10T00:00:00",
            }
        }



# ── Lo que se recibe al ACTUALIZAR un tratamiento ─────────
class TratamientoUpdate(BaseModel):
    nombre:       Optional[str]      = None
    descripcion:  Optional[str]      = None
    frecuencia:   Optional[str]      = None
    finalizacion: Optional[datetime] = None


# ── Lo que se DEVUELVE al consultar un tratamiento ────────
class TratamientoResponse(BaseModel):
    id_tratamiento: str
    id_mascota: str
    nombre: str
    descripcion: Optional[str]
    frecuencia: Optional[str]
    inicio: datetime
    finalizacion: Optional[datetime]

    class Config:
        from_attributes = True
