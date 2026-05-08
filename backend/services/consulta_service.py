from datetime import datetime
from sqlalchemy.orm import Session
from fastapi import HTTPException

from services import tratamiento_service, vacuna_service
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
        editado              = False,
        fecha_edicion        = None,
    )
    db.add(consulta)
    db.commit()
    db.refresh(consulta)  # actualiza el objeto con los datos generados por la BD 
 
    #flujos opcionales
 
    if data.crear_tratamiento and data.datos_tratamiento:

        tratamiento_service.crear_tratamiento(
            db=db,
            data=data.datos_tratamiento,
            id_consulta=consulta.id_consulta,
        )
        
    if (
        data.editar_tratamiento
        and data.id_tratamiento
        and data.datos_tratamiento
    ):

        tratamiento_service.actualizar_tratamiento(
            db=db,
            id_tratamiento=data.id_tratamiento,
            data=data.datos_tratamiento,
            id_consulta=consulta.id_consulta,
        )
 
    if data.agregar_dosis and data.datos_dosis:

        vacuna_service.registrar_dosis(
            db=db,
            data=data.datos_dosis,
            id_veterinaria=id_veterinario,
            id_consulta=consulta.id_consulta,
        )

 
    return consulta

def obtener_detalle(db: Session, id_consulta: str) -> dict:
    """
    Devuelve una consulta con los tratamientos y dosis creados en ella.
 

    """
    consulta = db.query(Consulta).filter(Consulta.id_consulta == id_consulta).first()
    if not consulta:
        raise HTTPException(status_code=404, detail="Consulta no encontrada")
 
    # trae solo los tratamientos creados en esta consulta
    tratamientos = (
        db.query(Tratamiento)
        .filter(Tratamiento.id_consulta_creacion == id_consulta)
        .order_by(Tratamiento.creacion.desc())
        .all()
    )
 
    # trae las dosis aplicadas en esta consulta.
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
        
        "tratamientos": [
            {
                "id_tratamiento": t.id_tratamiento,
                "nombre":      t.nombre,
                "descripcion": t.descripcion,
                "finalizacion": (str(t.finalizacion.date()) if t.finalizacion else None)
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
 

