from datetime import datetime
from pydantic import BaseModel, Field
from typing import Literal, Optional, List

from schemas.consulta import ConsultaResponse
from schemas.tratamiento import TratamientoResponse
from schemas.vacuna import EsquemaVacunacionResponse



# ── Lo que se DEVUELVE al visualizar el historial completo ─
class EventoConsulta(BaseModel):
    tipo: Literal["consulta"] = "consulta"
    fecha: datetime
    id: str
    motivo: str
    diagnostico: Optional[str]
    id_veterinario: str
 
    class Config:
        from_attributes = True
 
 
class EventoTratamiento(BaseModel):
    tipo: Literal["tratamiento"] = "tratamiento"
    fecha: datetime  # inicio del tratamiento
    id: str
    nombre: str
    descripcion: Optional[str]
    frecuencia: Optional[str]
    finalizacion: Optional[datetime]
 
    class Config:
        from_attributes = True
        
class HistorialUnificadoResponse(BaseModel):
    """
    Historial clínico completo con consultas y tratamientos intercalados
    """
    eventos: List[EventoConsulta | EventoTratamiento] = Field(
        description="Consultas y tratamientos ordenados cronológicamente (más reciente primero)"
    )
 
    class Config:
        from_attributes = True
        
        
