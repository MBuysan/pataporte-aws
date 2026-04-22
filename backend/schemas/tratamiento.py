from pydantic import BaseModel
from datetime import date
from datetime import datetime
from typing import Optional


# ── Lo que se recibe al CREAR un tratamiento ──────────────
class TratamientoCreate(BaseModel):
    # Este id lo genera la HU dependiente de consultas; KEY-7 solo lo utiliza.
    id_consulta: str
    nombre: str
    indicaciones: str
    fecha_inicio: date
    fecha_fin_estimada: date

    class Config:
        json_schema_extra = {
            "example": {
                "id_consulta": "uuid-de-la-consulta",
                "nombre": "Antibiótico 10 días",
                "indicaciones": "Amoxicilina 250mg cada 12hs",
                "fecha_inicio": "2024-06-01",
                "fecha_fin_estimada": "2024-06-10"
            }
        }

# ── Lo que se recibe al ACTUALIZAR un tratamiento ─────────
class TratamientoUpdate(BaseModel):
    nombre: Optional[str] = None
    indicaciones: Optional[str] = None
    fecha_inicio: Optional[date] = None
    fecha_fin_estimada: Optional[date] = None
    fecha_fin_real: Optional[date] = None


# ── Lo que se DEVUELVE al consultar un tratamiento ────────
class TratamientoResponse(BaseModel):
    id_tratamiento: str
    id_mascota: str
    id_consulta: str
    nombre: str
    indicaciones: str
    fecha_inicio: date
    fecha_fin_estimada: date
    fecha_fin_real: Optional[date] = None

    class Config:
        from_attributes = True
