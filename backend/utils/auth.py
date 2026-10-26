"""Autenticación común y controles de acceso a los recursos del usuario."""
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from config.database import get_db, Mascota, MascotaTutor, UsuarioTutor, Veterinario
from config.settings import settings
from utils.password_utils import oauth2_scheme


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM],
            options={"require": ["exp", "sub", "rol"]},
        )
        user_id = str(UUID(payload["sub"]))
        role = payload["rol"]
        if role not in ("tutor", "veterinario"):
            raise ValueError("Rol inválido")
    except (jwt.PyJWTError, ValueError, TypeError, KeyError) as exc:
        raise HTTPException(status_code=401, detail="Token inválido") from exc
    model = UsuarioTutor if role == "tutor" else Veterinario
    account = db.get(model, user_id)
    if not account or account.estado != "activo":
        raise HTTPException(status_code=401, detail="Cuenta no disponible")
    return {"id": user_id, "rol": role}


def require_tutor(user: dict = Depends(get_current_user)):
    if user["rol"] != "tutor":
        raise HTTPException(status_code=403, detail="Se requiere un tutor")
    return user


def get_current_tutor(user: dict = Depends(require_tutor)) -> str:
    return user["id"]


def get_current_vet(user: dict = Depends(get_current_user)) -> str:
    if user["rol"] != "veterinario":
        raise HTTPException(status_code=403, detail="Se requiere un veterinario")
    return user["id"]


def require_own_tutor(id_tutor: str, user: dict = Depends(require_tutor)):
    if user["id"] != id_tutor:
        raise HTTPException(status_code=403, detail="No autorizado")
    return user


def require_pet_access(db: Session, id_mascota: str, user: dict):
    try:
        id_mascota = str(UUID(id_mascota))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Mascota no encontrada") from exc
    pet = db.get(Mascota, id_mascota)
    if not pet:
        raise HTTPException(status_code=404, detail="Mascota no encontrada")
    if user["rol"] == "tutor":
        relation = db.get(MascotaTutor, (user["id"], id_mascota))
        if not relation:
            raise HTTPException(status_code=403, detail="No autorizado")
    # Política inicial: veterinarios activos atienden mascotas de la plataforma.
    # Una relación clínica más restrictiva requiere modelado de negocio adicional.
    return pet
