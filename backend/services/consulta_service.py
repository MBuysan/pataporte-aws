from datetime import datetime
from sqlalchemy.orm import Session
from fastapi import HTTPException

from schemas.consulta import ConsultaCreate, ConsultaUpdate
from config.database import Consulta, Mascota, Veterinaria, Tratamiento


def crear(db: Session, data: ConsultaCreate, id_veterinario: str):
    """
    Registra una consulta clinica.
    El id_veterinario viene del token JWT, no del body del request.
    La fecha_hora la pone el sistema, el veterinario no puede manipularla.
    """
    
    #verifica si la mascota existe y esté activa
    mascota = db.query(Mascota).filter(
        Mascota.id_mascota == data.id_mascota,
        Mascota.estado == "activo"
    ).first()
    if not mascota:
        raise HTTPException(status_code=404, detail="Mascota no encontrada o inactiva")
 
    # verifica que el veterinario existe y esté activo
    veterinario = db.query(Veterinaria).filter(
        Veterinaria.id_veterinaria == id_veterinario,
        Veterinaria.estado == "activo"
    ).first()
    if not veterinario:
        raise HTTPException(status_code=404, detail="Veterinario no encontrado o inactivo")
 
    # crea el objeto Consulta
    consulta = Consulta(
        id_mascota           = data.id_mascota,
        id_veterinario       = id_veterinario,
        fecha_hora           = datetime.utcnow(),
        motivo               = data.motivo,
        diagnostico          = data.diagnostico,
        tratamiento_indicado = data.tratamiento_indicado,
        editado              = False,
        fecha_edicion        = None,
    )
    db.add(consulta)
    db.commit()
    db.refresh(consulta)  # actualiza el objeto con los datos generados por la BD 
 
    #flujos opcionales
 
    if data.editar_tratamiento:
        pass  # llamar a tratamiento_service.crear() cuando este implementado
 
    if data.agregar_dosis:
        pass  # llamar a vacuna_service.registrar_dosis() cuando este implementado
 
    return consulta



