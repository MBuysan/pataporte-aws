from datetime import datetime, timezone
from sqlalchemy.orm import Session
from fastapi import HTTPException

from config.database import Consulta, Tratamiento ,EsquemaVacunacion
from services import mascota_service




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
    consultas = db.query(Consulta).filter(Consulta.id_mascota == id_mascota).all()

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

    #objeto a retornar, lista de eventos 
    eventos = []
    
    for c in consultas:
        eventos.append({
            "tipo":     "consulta",
            "fecha":    c.fecha_hora,
            "id":       c.id_consulta,
            "motivo":   c.motivo,
            "diagnostico":    c.diagnostico,
            "id_veterinario": c.id_veterinario,
        })
        
    for t in tratamientos:
        
        estado = (
        "FINALIZADO"
        if (
            t.finalizacion and
            t.finalizacion < datetime.now(timezone.utc)
        )
        else "ACTIVO"
    )

        eventos.append({
            "tipo": "tratamiento",
            "fecha": t.inicio,
            "id": t.id_tratamiento,
            "nombre": t.nombre,
            "descripcion": t.descripcion,
            "frecuencia": t.frecuencia,
            "finalizacion": t.finalizacion,
            "estado": estado,
            })
        

    #ordena todos los eventos del mas reciente al primero
    eventos.sort(key=lambda x: x["fecha"], reverse=True)
    
    return eventos

#comentario para que me deje pushear