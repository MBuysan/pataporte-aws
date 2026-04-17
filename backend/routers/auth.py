from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from config.database import get_db
from schemas.auth import LoginRequest, LoginResponse
from services import auth_service

router = APIRouter()


@router.post("/login", response_model=LoginResponse, summary="Iniciar sesión de tutor")
def login(data: LoginRequest, db: Session = Depends(get_db)):
    return auth_service.login_tutor(db, data.identificador, data.password)