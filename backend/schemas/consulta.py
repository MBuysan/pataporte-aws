from pydantic import BaseModel
from datetime import datetime
from typing import Optional


# ── Lo que se recibe al REGISTRAR una consulta ─────────────
class ConsultaCreate(BaseModel):
    id_mascota:           str
    motivo:               str
    diagnostico:          Optional[str]  = None
    tratamiento_indicado: Optional[str]  = None
    agregar_tratamiento:  Optional[bool] = False  # activa flujo de tratamiento_service
    agregar_dosis:        Optional[bool] = False  # activa flujo de vacuna_service
 
    class Config:
        json_schema_extra = {
            "example": {
                "id_mascota":           "uuid-de-la-mascota",
                "motivo":               "Control anual",
                "diagnostico":          "Animal sano",
                "tratamiento_indicado": "Ninguno",
                "agregar_tratamiento":  False,
                "agregar_dosis":        False,
            }
        }


# ── Lo que se recibe al EDITAR una consulta ────────────────
# Solo diagnostico y tratamiento son editables post-creacion
class ConsultaUpdate(BaseModel):
    diagnostico: Optional[str] = None
    tratamiento_indicado: Optional[str] = None


# ── Lo que se DEVUELVE al consultar una consulta ───────────
class ConsultaResponse(BaseModel):
    id_consulta: str
    id_mascota: str
    id_veterinario: str
    fecha_hora: datetime
    motivo: str
    diagnostico: Optional[str]
    tratamiento_indicado: Optional[str]
    editado: bool
    fecha_edicion: Optional[datetime]

    class Config:
        from_attributes = True
