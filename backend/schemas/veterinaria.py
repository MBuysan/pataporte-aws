from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime

class SucursalResponse(BaseModel):
    id_sucursal: str
    nombre: str
    estado: str

    class Config:
        from_attributes = True

class VeterinariaCreate(BaseModel):
    rut: str
    nombre: str
    email: EmailStr
    password: str

class VeterinariaResponse(BaseModel):
    id_veterinaria: str
    rut: str
    nombre: str
    email: EmailStr
    estado: str
    fecha_registro: datetime
    sucursales: List[SucursalResponse] = []

    class Config:
        from_attributes = True
