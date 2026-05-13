from datetime import datetime
from sqlalchemy.orm import Session
from fastapi import HTTPException

from config.database import Consulta, Tratamiento ,EsquemaVacunacion
from services import mascota_service

from schemas.consulta import ConsultaCreate


def ver_historial_consultas(db: Session, id_mascota: str) -> list[Consulta]:

    consultas = (
        db.query(Consulta).filter(Consulta.id_mascota == id_mascota).all()
    )

    return consultas


def obtener_historial_unificado(db: Session, id_mascota: str) -> list[dict]:
    
    """
    Devuelve consultas y tratamientos intercalados por fecha para el historial clínico.
    
    returns:
        lista de eventos ordenados cronológicamente (más reciente primero), donde cada evento tiene:
        - tipo: "consulta" | "tratamiento"
        - fecha: datetime del evento
        - datos: el objeto completo
    """

    mascota = mascota_service.obtener_por_id(db, id_mascota)
    if not mascota:
        raise HTTPException(status_code=404, detail="Mascota no encontrada")

    #  Consultas 
    consultas = ver_historial_consultas(db, id_mascota)

    #  Tratamientos 
    tratamientos = (
        db.query(Tratamiento)
        .filter(
            Tratamiento.id_mascota == id_mascota,
        ).all()
    )
    
    #  Vacunas 
    esquemas = (
        db.query(EsquemaVacunacion)
        .filter(EsquemaVacunacion.id_mascota == id_mascota)
        .all()
    )

    #objeto a retornar
    eventos = []
    
    for c in consultas:
        eventos.append({
            "tipo": "consulta",
            "fecha": c.fecha_hora,
            "datos": c
        })
        
    for t in tratamientos:
        eventos.append({
            "tipo": "tratamiento", 
            "fecha": t.inicio,
            "datos": t
        })
        
    """
    no se como funcionan los esquemas, queda comentado de momento
    for e in esquemas:
        eventos.append({
            "tipo": "tratamiento", 
            "fecha": t.inicio,
            "datos": t
        }) 
        
    """

    #ordena todos los eventos del mas reciente al primero
    eventos.sort(key=lambda x: x["fecha"], reverse=True)
    
    return eventos

