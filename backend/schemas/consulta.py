from schemas.vacuna import DosisResponse, DosisCreate
from schemas.tratamiento import TratamientoResponse, TratamientoUpdate, TratamientoCreate
from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional


# ── Lo que se recibe al REGISTRAR una consulta ─────────────
class ConsultaCreate(BaseModel):
    id_mascota:           str
    motivo:               str
    diagnostico:          Optional[str]  = None
    
    crear_tratamiento: bool = False
    editar_tratamiento: bool = False
    agregar_dosis: bool = False
    
    nuevo_tratamiento: Optional[TratamientoCreate] = None
    tratamiento_actualizado: Optional[TratamientoUpdate] = None
    nueva_dosis: Optional[DosisCreate] = None

    
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
    tratamientos: List[TratamientoResponse] = []
    dosis:        List[DosisResponse] = []
    
    class Config:
        from_attributes = True
