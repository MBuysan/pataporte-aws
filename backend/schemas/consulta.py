from schemas.vacuna import DosisResponse, DosisCreate, DosisDetalleConsultaResponse
from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional


# ── Lo que se recibe al REGISTRAR una consulta ─────────────
class ConsultaCreate(BaseModel):
    id_mascota:           str
    motivo:               str
    diagnostico:          Optional[str]  = None
    
    agregar_dosis: bool = False
    nueva_dosis: Optional[DosisCreate] = None

    
    class Config:
        json_schema_extra = {
            "example": {
                "id_mascota":       "uuid-mascota",
                "motivo":           "Control anual",
                "diagnostico":      "Animal sano",
                "agregar_dosis":    False,
            }
        }



# ── Lo que se DEVUELVE al consultar una consulta ───────────
class ConsultaResponse(BaseModel):
    id_consulta: str
    id_mascota: str
    id_veterinario: str
    fecha_hora: datetime
    motivo: str
    diagnostico: Optional[str]
    dosis:        List[DosisDetalleConsultaResponse] = []
    
    class Config:
        from_attributes = True
