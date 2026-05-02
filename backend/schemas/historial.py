from pydantic import BaseModel
from typing import Optional, List

from schemas.consulta import ConsultaResponse
from schemas.tratamiento import TratamientoResponse



# ── Lo que se DEVUELVE al visualizar el historial completo ─
class HistorialResponse(BaseModel):
    id_mascota: str
    nombre_mascota: str
    consultas: List[ConsultaResponse] = []
    tratamientos: List[TratamientoResponse] = []

    class Config:
        from_attributes = True
