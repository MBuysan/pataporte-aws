import uuid
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException
from passlib.context import CryptContext

from schemas.tutor import TutorCreate, TutorUpdate
from config.database import UsuarioTutor, MascotaTutor, Mascota

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def encriptar_pass(password: str) -> str:
    return pwd_context.hash(password)

def crear(db: Session, data: TutorCreate):
    """
    Registra un nuevo tutor.
    La cedula y el email son unicos — si ya existen lanza error.
    """
    try:
        nuevo_tutor = UsuarioTutor(
            id_tutor=str(uuid.uuid4()),
            nombre=data.nombre,
            cedula=data.cedula,
            email=data.email,
            telefono=data.telefono,
            password_hash=encriptar_pass(data.password),
            estado="activo"
        )

        db.add(nuevo_tutor)
        db.commit()
        db.refresh(nuevo_tutor)
        return nuevo_tutor

    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Ya existe un tutor con esa cedula o email")


def obtener_por_id(db: Session, id_tutor: str):
    """Busca un tutor por UUID."""
    pass


def obtener_por_cedula(db: Session, cedula: str):
    """
    Busca un tutor por cedula.
    Se usa en el router para evitar duplicados antes de crear.
    """
    pass


def actualizar(db: Session, id_tutor: str, data: TutorUpdate):
    """Actualiza nombre, email o telefono del tutor."""
    pass


def obtener_mascotas(db: Session, id_tutor: str):
    """
    Retorna todas las mascotas vinculadas a un tutor.
    Hace un join entre MASCOTA_TUTOR y MASCOTA.
    """
    pass


def vincular_mascota(db: Session, id_tutor: str, id_mascota: str, rol: str = "secundario"):
    """
    Vincula una mascota existente a un tutor adicional.
    Regla: solo puede haber un tutor principal por mascota.
    """
    pass