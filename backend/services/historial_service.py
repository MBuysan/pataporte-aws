import uuid
from datetime import datetime
from sqlalchemy.orm import Session
from fastapi import HTTPException

from schemas.historial import AgregarConsultaHistorialCreate
from config.database import Consulta, Tratamiento, Mascota ,EsquemaVacunacion
from services import mascota_service


def agregar_consulta_al_historial(
    db: Session, data: AgregarConsultaHistorialCreate, id_veterinario: str
) -> Consulta:

    mascota = mascota_service.obtener_por_id(db, Mascota.id_mascota)
    if not mascota:
        raise HTTPException(status_code=404, detail="Mascota no encontrada")

    nueva_consulta = Consulta(
        id_mascota=data.id_mascota,
        id_veterinario=id_veterinario,
        fecha_hora=datetime.utcnow(),
        motivo=data.motivo,
        diagnostico=data.diagnostico,
        tratamiento_indicado=data.tratamiento_indicado,
    )

    db.add(nueva_consulta)

    try:
        db.commit()
        db.refresh(nueva_consulta)
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Error al registrar la consulta")

    return nueva_consulta


def ver_historial_consultas(db: Session, id_mascota: str) -> list[Consulta]:

    consultas = (
        db.query(Consulta)
        .filter(Consulta.id_mascota == id_mascota)
        .order_by(Consulta.fecha_hora.desc())
        .all()
    )

    return consultas


def visualizar_historial(db: Session, id_mascota: str) -> dict:

    mascota = mascota_service.obtener_por_id(db, id_mascota)
    if not mascota:
        raise HTTPException(status_code=404, detail="Mascota no encontrada")

    #  Consultas 
    consultas = ver_historial_consultas(db, id_mascota)

    #  Tratamientos activos 
    tratamientos = (
        db.query(Tratamiento)
        .filter(
            Tratamiento.id_mascota == id_mascota,
            Tratamiento.finalizacion == None  # activos
        )
        .all()
    )

    #  Vacunas 
    esquemas = (
        db.query(EsquemaVacunacion)
        .filter(EsquemaVacunacion.id_mascota == id_mascota)
        .all()
    )

    return {
        "id_mascota": mascota.id_mascota,
        "nombre_mascota": mascota.nombre,
        "consultas": consultas,
        "tratamientos": tratamientos,
        "vacunas": esquemas,
    }
