from pydantic import BaseModel, EmailStr, field_validator
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

    @field_validator("rut")
    @classmethod
    def validar_rut(cls, v: str) -> str:
        rut = "".join(filter(str.isdigit, v.strip()))

        if len(rut) != 12:
            raise ValueError("El RUT debe tener 12 números")

        pesos = [4, 3, 2, 9, 8, 7, 6, 3, 4, 5, 2]
        suma = 0

        for i in range(11):
            suma += int(rut[i]) * pesos[i]

        digito = (10 - (suma % 10)) % 10

        if digito != int(rut[11]):
            raise ValueError("El RUT ingresado no es válido")

        return rut
    
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
