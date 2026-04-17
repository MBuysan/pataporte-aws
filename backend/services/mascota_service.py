import secrets
import string
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException

from schemas.mascota import MascotaCreate, MascotaUpdate
from config.database import Mascota, CodigoAccesoMascota


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



def generar_codigo_acceso(db: Session, id_mascota: str):
    """
    Genera un código único de 8 caracteres para compartir acceso.
    Expira en 24 horas.
    """
    mascota = obtener_por_id(db, id_mascota)
    if not mascota:
        raise HTTPException(status_code=404, detail="Mascota no encontrada")

    # Generar código alfanumérico aleatorio
    caracteres = string.ascii_uppercase + string.digits
    codigo = ''.join(secrets.choice(caracteres) for _ in range(8))

    # Definir expiración (24 horas)
    expiracion = datetime.utcnow() + timedelta(hours=24)

    nuevo_codigo = CodigoAccesoMascota(
        id_mascota=id_mascota,
        codigo=codigo,
        fecha_expiracion=expiracion
    )
    
    db.add(nuevo_codigo)
    try:
        db.commit()
        db.refresh(nuevo_codigo)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al generar el código: {str(e)}")
    
    return nuevo_codigo


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

