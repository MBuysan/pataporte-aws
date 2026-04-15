import uuid
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException
from passlib.context import CryptContext


from schemas.tutor import TutorCreate, TutorUpdate
from config.database import UsuarioTutor, MascotaTutor, Mascota

#config de encriptación
# ! no sé si esto está bien
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def encriptar_pass(password: str) -> str:
    return pwd_context.hash(password)

def crear(db: Session, data: TutorCreate):
    if obtener_por_cedula(db, data.cedula):
        raise ValueError("CEDULA_EXISTE")

    if obtener_por_email(db, data.email):
        raise ValueError("EMAIL_EXISTE")
    
    passwordenc =encriptar_pass(data.password)

    nuevo = UsuarioTutor(
        nombre=data.nombre,
        cedula=data.cedula,
        email=data.email,
        password=passwordenc,
        telefono=data.telefono
    )

    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return nuevo


def obtener_por_id(db: Session, id_tutor: str):
    return db.query(UsuarioTutor).filter(
        UsuarioTutor.id_tutor == id_tutor
    ).first()


def obtener_por_cedula(db: Session, cedula: str):
    return db.query(UsuarioTutor).filter(
        UsuarioTutor.cedula == cedula
    ).first()

def obtener_por_email(db: Session, email: str):
    return db.query(UsuarioTutor).filter(
        UsuarioTutor.email == email
    ).first()

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

