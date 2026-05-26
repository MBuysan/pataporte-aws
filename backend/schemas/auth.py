from pydantic import BaseModel
from typing import Literal


class LoginRequest(BaseModel):
    identificador: str
    password: str


class UserLoginResponse(BaseModel):
    id_tutor: str
    nombre: str
    email: str
    cedula: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"]
    user: UserLoginResponse


class VeterinarioLoginResponseData(BaseModel):
    id_veterinario:  str
    nombre:          str
    email:           str
    matricula:       str
    id_organizacion: str
 
 
class VeterinarioLoginResponse(BaseModel):
    access_token: str
    token_type:   Literal["bearer"]
    user:         VeterinarioLoginResponseData