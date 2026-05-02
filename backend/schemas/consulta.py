from schemas.tratamiento import TratamientoUpdate
from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional


# ── Lo que se recibe al REGISTRAR una consulta ─────────────
class ConsultaCreate(BaseModel):
    id_mascota:           str
    motivo:               str
    diagnostico:          Optional[str]  = None
    editar_tratamiento:  Optional[bool] = False  # activa flujo de tratamiento_service
    agregar_dosis:        Optional[bool] = False  # activa flujo de vacuna_service
    id_tratamiento:     Optional[str]             = None
    datos_tratamiento:  Optional[TratamientoUpdate] = None
    
    
    class Config:
        json_schema_extra = {
            "example": {
                "id_mascota":       "uuid-mascota",
                "motivo":           "Control anual",
                "diagnostico":      "Animal sano",
                "agregar_dosis":    False,
                "editar_tratamiento": True,
                "id_tratamiento":   "uuid-tratamiento",
                "datos_tratamiento": {
                    "nombre":       "Vitaminas diarias",
                    "descripcion":  "Una pastilla por día",
                    "finalizacion": None,
                },
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
    tratamientos: Optional[List[dict]] = None
    dosis:        Optional[List[dict]] = None
    
    class Config:
        from_attributes = True
