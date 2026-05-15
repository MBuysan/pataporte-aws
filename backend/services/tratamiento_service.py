import uuid
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from fastapi import HTTPException

from schemas.tratamiento import TratamientoCreate, TratamientoUpdate
from config.database import Tratamiento, Mascota

 
def crear_tratamiento(db: Session,id_mascota: str,data: TratamientoCreate) -> Tratamiento:
    """
    Crea un nuevo tratamiento asociado a una consulta.
    """

    mascota = (
        db.query(Mascota)
        .filter(
            Mascota.id_mascota == id_mascota,
            Mascota.estado == "activo"
        )
        .first()
    )

    if not mascota:
        raise HTTPException(
            status_code=404,
            detail="Mascota no encontrada o inactiva"
        )

    duplicado = (
        db.query(Tratamiento)
        .filter(
            Tratamiento.id_mascota == id_mascota,
            Tratamiento.nombre == data.nombre
        )
        .first()
    )

    if duplicado:
        raise HTTPException(
            status_code=409,
            detail="Ya existe un tratamiento con ese nombre para esta mascota"
        )

    _check_fecha_finalizacion(data.finalizacion, data.inicio)
    
    tratamiento = Tratamiento(
        id_mascota=id_mascota,
        nombre=data.nombre,
        descripcion=data.descripcion,
        frecuencia = data.frecuencia,
        inicio = data.inicio,
        finalizacion= data.finalizacion
    )

    db.add(tratamiento)
    db.commit()
    db.refresh(tratamiento)

    return tratamiento


def ver_tratamientos_activos(db: Session, id_mascota: str) -> list[Tratamiento]:

    mascota = db.query(Mascota).filter(Mascota.id_mascota == id_mascota).first()

    if not mascota:
        raise HTTPException(status_code=404, detail="Mascota no encontrada")

    return (
        db.query(Tratamiento)
        .filter(
            Tratamiento.id_mascota == id_mascota,
            (Tratamiento.finalizacion == None) |
            (Tratamiento.finalizacion > datetime.utcnow())
        )
        .order_by(Tratamiento.inicio.desc())
        .all()
    )


def listar_por_mascota(db: Session, id_mascota: str) -> list[Tratamiento]:
    """
    Retorna todos los tratamientos (activos e históricos) de una mascota.
    """
    mascota = db.query(Mascota).filter(Mascota.id_mascota == id_mascota).first()
    if not mascota:
        raise HTTPException(status_code=404, detail="Mascota no encontrada")
 
    return (
        db.query(Tratamiento)
        .filter(Tratamiento.id_mascota == id_mascota)
        .order_by(Tratamiento.inicio.desc())
        .all()
    )


def obtener_por_id(db: Session, id_tratamiento: str) -> Tratamiento:

    tratamiento = (
        db.query(Tratamiento)
        .filter(Tratamiento.id_tratamiento == id_tratamiento)
        .first()
    )

    if not tratamiento:
        raise HTTPException(status_code=404, detail="Tratamiento no encontrado")

    return tratamiento


def actualizar_tratamiento(db: Session, id_tratamiento: str, data: TratamientoUpdate) -> Tratamiento:

    tratamiento = obtener_por_id(db, id_tratamiento)
    
    if tratamiento.finalizacion and tratamiento.finalizacion < datetime.utcnow():
        raise HTTPException(
            status_code=400,
            detail="No se pueden editar tratamientos finalizados"
        )
        
    hubo_cambios = False
        
    if (data.nombre is not None and data.nombre != tratamiento.nombre):

        colision = (
            db.query(Tratamiento)
            .filter(
                Tratamiento.id_mascota == tratamiento.id_mascota,
                Tratamiento.nombre == data.nombre,
                Tratamiento.id_tratamiento != id_tratamiento
            )
            .first()
        )

        if colision:
            raise HTTPException(
                status_code=409,
                detail="Ya existe un tratamiento con ese nombre para esta mascota"
            )

        tratamiento.nombre = data.nombre
        hubo_cambios = True

    if data.descripcion is not None and data.descripcion != tratamiento.descripcion:  
        
        tratamiento.descripcion = data.descripcion
        hubo_cambios = True

    if data.frecuencia is not None and data.frecuencia != tratamiento.frecuencia: 
        
        tratamiento.frecuencia = data.frecuencia
        hubo_cambios = True
    
    
    fecha_inicio = data.inicio or tratamiento.inicio
    fecha_finalizacion= (data.finalizacion if data.finalizacion is not None else tratamiento.finalizacion)
    
    _check_fecha_finalizacion(fecha_finalizacion,fecha_inicio)
    
    if data.inicio is not None and data.inicio != tratamiento.inicio:

        tratamiento.inicio = data.inicio
        hubo_cambios = True
        
    if (data.finalizacion is not None and data.finalizacion != tratamiento.finalizacion):  
        
        tratamiento.finalizacion = data.finalizacion
        hubo_cambios = True
        
        
    if not hubo_cambios:
        raise HTTPException(
            status_code=400,
            detail="No se proporcionaron cambios para actualizar"
        )
        
    tratamiento.editado = True
    tratamiento.fecha_edicion = datetime.utcnow()

    db.commit()
    db.refresh(tratamiento)

    return tratamiento


def _check_fecha_finalizacion(finalizacion: datetime | None, inicio: datetime) -> None:

    if finalizacion < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=400,
            detail="La fecha de finalización no puede ser anterior a la actual"
        )

    if inicio and finalizacion < inicio:
        raise HTTPException(
            status_code=400,
            detail="La fecha de finalización no puede ser anterior al inicio"
        )