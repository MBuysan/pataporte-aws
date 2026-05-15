import secrets
import string
from datetime import date, datetime, timedelta, timezone
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException

from schemas.mascota import MascotaCreate, MascotaUpdate
from config.database import Mascota, CodigoAccesoMascota, UsuarioTutor, MascotaTutor


def listar(db: Session):
    return db.query(Mascota).filter(Mascota.estado == "activo").all()


def obtener_por_id(db: Session, id_mascota: str):
    return db.query(Mascota).filter(Mascota.id_mascota == id_mascota).first()


def crear(db: Session, data: MascotaCreate):
    """
    *Funcionalidad:*
    Crear una nueva mascota con id único generado por el sistema y asociarlo con el tutor

    *Retorna:*
    nueva_mascota[obj]

    *Validaciones:*
        1) Valida si existe el tutor, en caso de que no, lanza excepción 404
        2) Valida si existe actualmente una mascota con el mismo: nombre, especie y feha de nacimiento para ese tutor, en caso de que no, lanza excepción 409
        3) Si por cualquier motivo el sistema no consigue almacenar la nueva mascota y su relacion con el tutor en la base de datos, lanza excepción 500

    *Información adicional:*

    .add() -> añade a la BD

    .flush() -> borra el buffer interno y fuerza a que todos los datos que el dato almacenado se escriba inmediatamente en su destino

    """
    tutor = (
        db.query(UsuarioTutor).filter(UsuarioTutor.id_tutor == data.id_tutor).first()
    )
    if not tutor:
        raise HTTPException(status_code=404, detail="Tutor no encontrado")

    duplicado = (
        db.query(Mascota)
        .join(MascotaTutor, Mascota.id_mascota == MascotaTutor.id_mascota)
        .filter(
            MascotaTutor.id_tutor == data.id_tutor,
            Mascota.nombre == data.nombre,
            Mascota.especie == data.especie,
            Mascota.fecha_de_nacimiento == data.fecha_de_nacimiento,
        )
        .first()
    )
    if duplicado:
        raise HTTPException(
            status_code=409,
            detail="Ya existe una mascota con ese nombre, especie y fecha de nacimiento para este tutor",
        )

    nueva_mascota = Mascota(
        nombre=data.nombre,
        especie=data.especie,
        raza=data.raza,
        fecha_de_nacimiento=data.fecha_de_nacimiento,
        sexo=data.sexo,
        foto_url=data.foto_url,
    )

    db.add(nueva_mascota)
    db.flush()

    vinculo_mascota_tutor = MascotaTutor(
        id_tutor=data.id_tutor,
        id_mascota=nueva_mascota.id_mascota,
        rol_tutor="principal",
    )
    db.add(vinculo_mascota_tutor)

    try:
        db.commit()
        db.refresh(nueva_mascota)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=500, detail="Error al registrar la mascota")

    return nueva_mascota


def calcular_edad(mascota) -> int | None:
    """
    calcula la edad en años a partir de la fecha de nacimiento.
    devuelve none si la mascota no tiene fecha de nacimiento registrada.
 
    """
    if not mascota.fecha_de_nacimiento:
        return None
    hoy = date.today()
    # resta 1 si todavía no llegó el cumpleaños este año
    return (
        hoy.year - mascota.fecha_de_nacimiento.year
        - ((hoy.month, hoy.day) < (mascota.fecha_de_nacimiento.month, mascota.fecha_de_nacimiento.day))
    )



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
    codigo = "".join(secrets.choice(caracteres) for _ in range(8))

    # Definir expiración (24 horas)
    expiracion = datetime.utcnow() + timedelta(hours=24)

    nuevo_codigo = CodigoAccesoMascota(
        id_mascota=id_mascota, codigo=codigo, fecha_expiracion=expiracion
    )

    db.add(nuevo_codigo)
    try:
        db.commit()
        db.refresh(nuevo_codigo)
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500, detail=f"Error al generar el código: {str(e)}"
        )

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
