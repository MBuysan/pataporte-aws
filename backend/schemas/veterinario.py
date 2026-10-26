from pydantic import BaseModel, EmailStr, field_validator
from typing import List, Optional
from datetime import datetime
from utils.password_utils import validar_password


class VeterinarioCreate(BaseModel):
    rut_organizacion: str
    matricula: str
    nombre: str
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def validar_clave(cls, value: str) -> str:
        validar_password(value)
        return value

    @field_validator("rut_organizacion")
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
    
    @field_validator("matricula")
    @classmethod
    def validar_matricula(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("La matrícula no puede estar vacía")
        return v
    

class OrganizacionResponse(BaseModel):
    id_organizacion: str
    rut:             str
    fecha_registro:  datetime
 
    class Config:
        from_attributes = True
 

class VeterinarioResponse(BaseModel):
    id_veterinario: str
    matricula: str
    nombre: str
    email: EmailStr
    estado: str
    fecha_registro: datetime
    organizacion: OrganizacionResponse

    class Config:
        from_attributes = True
