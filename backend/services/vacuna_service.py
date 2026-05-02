import uuid
import hashlib
from datetime import date, timedelta
from sqlalchemy.orm import Session
from fastapi import HTTPException

from schemas.vacuna import DosisCreate
from config.database import Dosis, EsquemaVacunacion, Certificado, EsquemaVacuna, TipoVacunas

def crear_esquema(db: Session, id_mascota: str):
    esquema = EsquemaVacunacion(
        id_esquema=str(uuid.uuid4()),
        id_mascota=id_mascota,
        fecha_inicio=date.today(),
        estado="activo"
    )

    db.add(esquema)
    db.commit()
    db.refresh(esquema)

    return esquema

def agregar_vacuna_a_esquema(db: Session, id_esquema: str, id_vacuna: str):

    esquema = db.query(EsquemaVacunacion).filter_by(
        id_esquema=id_esquema
    ).first()

    if not esquema:
        raise HTTPException(status_code=404, detail="Esquema no existe")

    vacuna = db.query(TipoVacunas).filter_by(
        id_vacuna=id_vacuna
    ).first()

    if not vacuna:
        raise HTTPException(status_code=404, detail="Vacuna no existe")

    existe = db.query(EsquemaVacuna).filter_by(
        id_esquema=id_esquema,
        id_vacuna=id_vacuna
    ).first()

    if existe:
        raise HTTPException(status_code=400, detail="La vacuna ya está en el esquema")

    esquema_vacuna = EsquemaVacuna(
        id_esquema_vacuna=str(uuid.uuid4()),
        id_esquema=id_esquema,
        id_vacuna=id_vacuna,
        estado="activo",
        fecha_proxima_dosis=None
    )

    db.add(esquema_vacuna)
    db.commit()
    db.refresh(esquema_vacuna)

    return esquema_vacuna

def registrar_dosis(db: Session, data: DosisCreate, id_veterinaria: str):
    esquema_vacuna = db.query(EsquemaVacuna).filter_by(
        id_esquema_vacuna=data.id_esquema_vacuna
    ).first()

    if not esquema_vacuna:
        raise HTTPException(status_code=404, detail="Vacuna no encontrada en el esquema")

    existe = db.query(Dosis).filter_by(
        id_esquema_vacuna=data.id_esquema_vacuna,
        numero_dosis=data.numero_dosis
    ).first()

    if existe:
        raise HTTPException(status_code=400, detail="Dosis ya registrada")

    dosis = Dosis(
        id_dosis=str(uuid.uuid4()),
        id_esquema_vacuna=data.id_esquema_vacuna,
        id_veterinaria=id_veterinaria,
        numero_dosis=data.numero_dosis,
        fecha_aplicacion=data.fecha_aplicacion,
        lote_vacuna=data.lote_vacuna,
        via_administracion=data.via_administracion,
        observaciones=data.observaciones,
        es_externa=data.es_externa
    )

    db.add(dosis)
    db.flush()

    _generar_certificado(db, dosis)
    _actualizar_proxima_dosis(db, dosis)

    db.commit()
    db.refresh(dosis)

    return dosis


def esquema_por_mascota(db: Session, id_mascota: str):
    esquemas = db.query(EsquemaVacunacion).filter_by(
        id_mascota=id_mascota
    ).all()

    if not esquemas:
        return []

    resultado = []

    for esquema in esquemas:
        vacunas = db.query(EsquemaVacuna).filter_by(
            id_esquema=esquema.id_esquema
        ).all()

        vacunas_response = []

        for ev in vacunas:
            tipo = db.query(TipoVacunas).filter_by(
                id_vacuna=ev.id_vacuna
            ).first()

            dosis = db.query(Dosis).filter_by(
                id_esquema_vacuna=ev.id_esquema_vacuna
            ).all()

            vacunas_response.append({
                "id_esquema_vacuna": ev.id_esquema_vacuna,
                "id_vacuna": ev.id_vacuna,
                "nombre": tipo.nombre if tipo else "Sin nombre",
                "estado": ev.estado,
                "fecha_inicio": esquema.fecha_inicio,
                "fecha_proxima_dosis": ev.fecha_proxima_dosis,
                "dosis": dosis
            })

        resultado.append({
            "id_esquema": esquema.id_esquema,
            "id_mascota": esquema.id_mascota,
            "vacunas": vacunas_response
        })

    return resultado


def _generar_certificado(db: Session, dosis: Dosis):
    """
    Funcion privada. Genera el certificado de la dosis.
    - Vet interno: estado = 'vigente'
    - Vet externo: estado = 'pendiente_revision' (regla 3.4.5)
    """
    pass


def _actualizar_proxima_dosis(db: Session, dosis: Dosis):
    """
    Funcion privada. Recalcula la fecha de la proxima dosis en el esquema
    usando el intervalo definido en TipoVacunas.
    """
    pass
