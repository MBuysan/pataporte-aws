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

class VeterinariaLoginResponseData(BaseModel):
    id_veterinaria: str
    nombre: str
    email: str
    rut: str

class VeterinariaLoginResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"]
    user: VeterinariaLoginResponseData
