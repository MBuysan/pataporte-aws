from datetime import datetime, timedelta, timezone

import jwt
from fastapi import HTTPException
from passlib.context import CryptContext
from sqlalchemy import or_
from sqlalchemy.orm import Session

from config.database import UsuarioTutor
from config.settings import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verificar_password(password_plano: str, password_hash: str) -> bool:
    try:
        return pwd_context.verify(password_plano, password_hash)
    except ValueError:
        return False


def crear_access_token(data: dict) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )

    payload = data.copy()
    payload.update({"exp": expire})

    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return token


def login_tutor(db: Session, identificador: str, password: str):
    tutor = (
        db.query(UsuarioTutor)
        .filter(
            UsuarioTutor.estado == "activo",
            or_(
                UsuarioTutor.email == identificador,
                UsuarioTutor.cedula == identificador,
            ),
        )
        .first()
    )

    if not tutor:
        raise HTTPException(status_code=401, detail="Credenciales inválidas")

    if not verificar_password(password, tutor.password_hash):
        raise HTTPException(status_code=401, detail="Credenciales inválidas")

    access_token = crear_access_token(
        {
            "sub": tutor.id_tutor,
            "rol": "tutor",
            "nombre": tutor.nombre,
            "email": tutor.email,
        }
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id_tutor": tutor.id_tutor,
            "nombre": tutor.nombre,
            "email": tutor.email,
            "cedula": tutor.cedula,
        },
    }