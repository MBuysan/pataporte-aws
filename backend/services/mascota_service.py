import uuid
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException

from schemas.mascota import MascotaCreate, MascotaUpdate
from config.database import Mascota, MascotaTutor


def listar(db: Session):
    return db.query(Mascota).filter(Mascota.estado == "activo").all()


def obtener_por_id(db: Session, id_mascota: str):
    return db.query(Mascota).filter(Mascota.id_mascota == id_mascota).first()


def crear(db: Session, data: MascotaCreate):
    """
    Crea una nueva mascota con UUID generado por el sistema.
    El id_mascota lo genera el backend, no el usuario.
    """
    pass


def actualizar(db: Session, id_mascota: str, data: MascotaUpdate):
    """
    Actualiza solo los campos que llegaron (los None se ignoran).
    No permite modificar especie ni fecha de registro.
    """
    pass


def eliminar(db: Session, id_mascota: str):
    """
    Antes de eliminar, envia el historial clinico al tutor por email.
    Regla de negocio: el tutor debe recibir toda la informacion antes del borrado.
    """
    pass


def _enviar_historial_por_email(db: Session, mascota):
    """
    Funcion privada. Recopila el historial y lo envia al correo del tutor.
    TODO: implementar con libreria de email (sendgrid, smtp, etc.)
    """
    pass

