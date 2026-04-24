import uuid
import hashlib
from datetime import date, timedelta
from sqlalchemy.orm import Session
from fastapi import HTTPException

from schemas.vacuna import DosisCreate
from config.database import Dosis, EsquemaVacunacion, Certificado, Mascota


def registrar_dosis(db: Session, data: DosisCreate, id_veterinaria: str):
    """
    Registra la aplicacion de una dosis y genera su certificado automaticamente.
    Si la dosis es externa (es_externa=True), el certificado queda en
    estado 'pendiente_revision' hasta que un admin lo valide (regla 3.4.5).
    """
    pass


def esquema_por_mascota(db: Session, id_mascota: str):
    mascota = (
        db.query(Mascota)
        .filter(Mascota.id_mascota == id_mascota)
        .first()
    )

    if not mascota:
        raise HTTPException(status_code=404, detail="Mascota no encontrada")

    esquemas = (
        db.query(EsquemaVacunacion)
        .filter(EsquemaVacunacion.id_mascota == id_mascota)
        .order_by(EsquemaVacunacion.fecha_inicio.desc())
        .all()
    )

    respuesta = []
    hoy = date.today()

    for esquema in esquemas:
        dosis = (
            db.query(Dosis)
            .filter(Dosis.id_esquema == esquema.id_esquema)
            .order_by(Dosis.numero_dosis.asc())
            .all()
        )

        dosis_totales = esquema.tipo_vacuna.cantidad_dosis_requeridas
        dosis_dadas = len(dosis)
        esquema_completo = dosis_dadas >= dosis_totales

        fecha_estimada_fin = None
        if esquema.tipo_vacuna.intervalo_entre_dosis_dias is not None:
            fecha_estimada_fin = esquema.fecha_inicio + timedelta(
                days=esquema.tipo_vacuna.intervalo_entre_dosis_dias * (dosis_totales - 1)
            )

        proxima_a_vencer = (
            not esquema_completo
            and esquema.fecha_proxima_dosis is not None
            and esquema.fecha_proxima_dosis <= hoy + timedelta(days=7)
        )

        respuesta.append(
            {
                "id_esquema": esquema.id_esquema,
                "id_mascota": esquema.id_mascota,
                "nombre_vacuna": esquema.tipo_vacuna.nombre,
                "fecha_inicio": esquema.fecha_inicio,
                "estado": esquema.estado,
                "fecha_proxima_dosis": None if esquema_completo else esquema.fecha_proxima_dosis,
                "fecha_estimada_fin": fecha_estimada_fin,
                "dosis_totales": dosis_totales,
                "dosis_dadas": dosis_dadas,
                "esquema_completo": esquema_completo,
                "proxima_a_vencer": proxima_a_vencer,
                "dosis": dosis,
            }
        )

    return respuesta


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