"""Dependencias de autenticación JWT compartidas por los routers."""
import jwt
from fastapi import Depends, HTTPException
from jwt import PyJWTError

from config.settings import settings
from utils.password_utils import oauth2_scheme


def _decodificar(token: str) -> dict:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except PyJWTError:
        raise HTTPException(status_code=401, detail="No autorizado")


def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    """Tutor o veterinario: devuelve {"id", "rol"}."""
    payload = _decodificar(token)
    sub, rol = payload.get("sub"), payload.get("rol")
    if not sub or rol not in ("veterinario", "tutor"):
        raise HTTPException(status_code=401, detail="Token inválido")
    return {"id": sub, "rol": rol}


def get_current_vet(token: str = Depends(oauth2_scheme)) -> str:
    """Solo veterinarios: devuelve el id_veterinario."""
    payload = _decodificar(token)
    if payload.get("rol") != "veterinario":
        raise HTTPException(status_code=401, detail="No autorizado")
    sub = payload.get("sub")
    if not sub:
        raise HTTPException(status_code=401, detail="Token inválido")
    return sub


def get_current_tutor(token: str = Depends(oauth2_scheme)) -> str:
    """Devuelve el sub del token. No valida el rol: los veterinarios también usan /mascotas."""
    sub = _decodificar(token).get("sub")
    if not sub:
        raise HTTPException(status_code=401, detail="Token inválido")
    return sub
