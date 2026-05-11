from pydantic import BaseModel
from typing import Optional, List

from schemas.consulta import ConsultaResponse
from schemas.tratamiento import TratamientoResponse
from schemas.vacuna import EsquemaVacunacionResponse



# ── Lo que se DEVUELVE al visualizar el historial completo ─
class HistorialResponse(BaseModel):
    id_mascota: str
    nombre_mascota: str
    consultas: List[ConsultaResponse] = []
    tratamientos: List[TratamientoResponse] = []
    vacunas: List[EsquemaVacunacionResponse] = [] 

    class Config:
        from_attributes = True
