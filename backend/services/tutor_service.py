import uuid
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException
from passlib.context import CryptContext


from datetime import datetime
from schemas.tutor import TutorCreate, TutorUpdate
from config.database import MascotaTutor, CodigoAccesoMascota

#config de encriptación
# ! no sé si esto está bien
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def encriptar_pass(password: str) -> str:
    return pwd_context.hash(password)

def crear(db: Session, data: TutorCreate):
    """
    Registra un nuevo tutor.
    La cedula y el email son unicos — si ya existen lanza error.
    """
    pass


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
    Vincula una mascota existente a un tutor.
    """
    vinculo = MascotaTutor(
        id_tutor=id_tutor,
        id_mascota=id_mascota,
        rol_tutor=rol
    )
    db.add(vinculo)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="El tutor ya está vinculado a esta mascota")


def vincular_mascota_con_codigo(db: Session, id_tutor: str, codigo: str):
    """
    Vincula una mascota usando un código de acceso.
    """
    # 1. Validar código
    codigo_obj = db.query(CodigoAccesoMascota).filter(
        CodigoAccesoMascota.codigo == codigo,
        CodigoAccesoMascota.usado == False
    ).first()

    if not codigo_obj:
        raise HTTPException(status_code=404, detail="Código no encontrado o ya utilizado")

    # 2. Validar expiración
    if codigo_obj.fecha_expiracion < datetime.utcnow():
        raise HTTPException(status_code=400, detail="El código ha expirado")

    # 3. Vincular (rol secundario por defecto)
    vincular_mascota(db, id_tutor, codigo_obj.id_mascota, rol="secundario")

    # 4. Marcar código como usado
    codigo_obj.usado = True
    db.commit()

    # 5. Notificar al tutor (Simulado por print en el server)
    tutor_nuevo = obtener_por_id(db, id_tutor)
    print(f"NOTIFICACIÓN: El usuario {tutor_nuevo.nombre} ha sido agregado como co-tutor de la mascota {codigo_obj.id_mascota}")

    return {"message": "Mascota vinculada exitosamente"}

