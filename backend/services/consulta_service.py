from datetime import datetime
from sqlalchemy.orm import Session
from fastapi import HTTPException

from schemas.consulta import ConsultaCreate
from config.database import Consulta, Dosis, EsquemaVacuna, Mascota, TipoVacunas, Veterinaria, Tratamiento


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

def obtener_detalle(db: Session, id_consulta: str) -> dict:
    """
    Devuelve una consulta con los tratamientos y dosis creados en ella.
 
    Gracias a que Tratamiento.id_consulta y Dosis.id_consulta existen
    como FK opcionales en la DB, podemos filtrar exactamente lo que
    ocurrió en esta consulta específica — sin depender de los services
    de los compañeros y sin traer datos de otras consultas.
 
    ondelete="SET NULL" en ambas FK significa que si la consulta se
    eliminara, tratamientos y dosis quedan huérfanos pero no se borran.
    """
    consulta = db.query(Consulta).filter(Consulta.id_consulta == id_consulta).first()
    if not consulta:
        raise HTTPException(status_code=404, detail="Consulta no encontrada")
 
    # trae solo los tratamientos creados en esta consulta
    tratamientos = (
        db.query(Tratamiento)
        .filter(Tratamiento.id_consulta == id_consulta)
        .order_by(Tratamiento.creacion.desc())
        .all()
    )
 
    # trae las dosis aplicadas en esta consulta.
    # hace join con EsquemaVacuna → TipoVacunas para obtener el nombre
    # de la vacuna, ya que Dosis solo guarda el id del esquema.
    dosis = (
        db.query(Dosis, TipoVacunas.nombre)
        .join(EsquemaVacuna, Dosis.id_esquema_vacuna == EsquemaVacuna.id_esquema_vacuna)
        .join(TipoVacunas,   EsquemaVacuna.id_vacuna == TipoVacunas.id_vacuna)
        .filter(Dosis.id_consulta == id_consulta)
        .all()
    )
 
    return {
        "id_consulta":          consulta.id_consulta,
        "id_mascota":           consulta.id_mascota,
        "id_veterinario":       consulta.id_veterinario,
        "fecha_hora":           consulta.fecha_hora,
        "motivo":               consulta.motivo,
        "diagnostico":          consulta.diagnostico,
        "tratamiento_indicado": consulta.tratamiento_indicado,
        "tratamientos": [
            {
                "nombre":      t.nombre,
                "descripcion": t.descripcion,
                "finalizacion": str(t.finalizacion.date()) if t.finalizacion else None,
            }
            for t in tratamientos
        ],
        "dosis": [
            {
                "nombre_vacuna":   nombre_vacuna,
                "numero_dosis":    d.numero_dosis,
                "fecha_aplicacion": str(d.fecha_aplicacion),
            }
            for d, nombre_vacuna in dosis
        ],
    }
 

