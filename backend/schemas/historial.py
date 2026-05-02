from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List

from schemas.consulta import ConsultaResponse
from schemas.tratamiento import TratamientoResponse
from schemas.vacuna import EsquemaVacunacionResponse


# ── Lo que se recibe al AGREGAR una consulta al historial ─
class AgregarConsultaHistorialCreate(BaseModel):
    id_mascota: str
    motivo: str
    diagnostico: Optional[str] = None
    tratamiento_indicado: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "id_mascota": "uuid-de-la-mascota",
                "motivo": "Vómitos frecuentes",
                "diagnostico": "Gastritis leve",
                "tratamiento_indicado": "Dieta blanda por 48 horas",
            }
        }


# ── Lo que se DEVUELVE al visualizar el historial completo ─
class HistorialResponse(BaseModel):
    id_mascota: str
    nombre_mascota: str
    consultas: List[ConsultaResponse] = []
    tratamientos: List[TratamientoResponse] = []
    vacunas: List[EsquemaVacunacionResponse] = [] 

    class Config:
        from_attributes = True
