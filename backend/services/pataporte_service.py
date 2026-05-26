import uuid
from datetime import datetime
from sqlalchemy.orm import Session
from fastapi import HTTPException

from config.database import (
    Mascota,
    MascotaTutor,
    UsuarioTutor,
    EsquemaVacunacion,
    EsquemaVacuna,
    Dosis,
    TipoVacunas,
    Veterinario,
    Organizacion,
    Pataporte,
)


def ver_pataporte(db: Session, id_mascota: str) -> dict:
    """
    Retorna el pataporte digital completo de una mascota:
    datos de identidad, tutor principal y esquemas de vacunación con sus dosis.
    """
    pass


def generar_pataporte(db: Session, id_mascota: str, id_veterinario: str) -> Pataporte:
    """
    Genera (o actualiza) el pataporte digital de una mascota.
    Alias de ver_pataporte con intención de persistencia futura
    (p. ej. generar PDF o URL pública).
    Retorna los mismos datos que ver_pataporte.
    """
    
    mascota = db.query(Mascota).filter(Mascota.id_mascota == id_mascota).first()
    if not mascota:
        raise HTTPException(status_code=404, detail="Mascota no encontrada")

    veterinario = db.query(Veterinario).filter(Veterinario.id_veterinario == id_veterinario).first()
    if not veterinario:
        raise HTTPException(status_code=404, detail="Veterinario no encontrado")

    
    organizacion = db.query(Organizacion).filter(Organizacion.id_organizacion == veterinario.id_organizacion).first()
    if not organizacion:
        raise HTTPException(status_code=404, detail="Organización del veterinario no encontrada")
    
    
    tutor = (
        db.query(UsuarioTutor)
        .join(MascotaTutor, UsuarioTutor.id_tutor == MascotaTutor.id_tutor)
        .filter(MascotaTutor.id_mascota == id_mascota)
        .first()
    )
    if not tutor:
        raise HTTPException(status_code=404, detail="Tutor no encontrado")
    
    esquemas = (
        db.query(EsquemaVacunacion)
        .filter(EsquemaVacunacion.id_mascota == id_mascota)
        .all()
    )
    
    #deprecar pataporte vigente anterior
    db.query(Pataporte).filter(Pataporte.id_mascota == id_mascota, Pataporte.fecha_generacion < datetime.utcnow()).update({"vigente": False})

    # Lógica para generar el pataporte (simplificada)
    pataporte = Pataporte(
        id_mascota=id_mascota,
        id_veterinario=id_veterinario,
        fecha_generacion=datetime.utcnow()
    )
    db.add(pataporte)
    db.commit()
    db.refresh(pataporte)
    return pataporte

