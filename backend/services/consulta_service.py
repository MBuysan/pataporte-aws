from datetime import datetime, timezone
from sqlalchemy.orm import Session
from fastapi import HTTPException

from services import tratamiento_service, vacuna_service
from schemas.consulta import ConsultaCreate
from config.database import Consulta, Dosis, EsquemaVacuna, EsquemaVacunacion, Mascota, TipoVacunas, Veterinaria, Tratamiento


def crear(db: Session, data: ConsultaCreate, id_veterinario: str):
    """
    Registra una consulta con sus vacunas y dosis en una sola transacción.
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
        fecha_hora           = datetime.now(timezone.utc),
        motivo               = data.motivo,
        diagnostico          = data.diagnostico,
        tratamiento_indicado = None,
        editado              = False,
        fecha_edicion        = None,
    )
    db.add(consulta)
    db.flush()  # para generar el id_consulta antes de hacer otras operaciones que lo necesitan
    
    requiere_esquema = mascota.especie != "otro"
    
    esquema = None
    
    if requiere_esquema:
        
        esquema = db.query(EsquemaVacunacion).filter_by(
            id_mascota=data.id_mascota
        ).first()
        if not esquema:
            raise HTTPException(status_code=404, detail="La mascota no tiene esquema de vacunación")

    
        esquemas_nuevos: dict = {}
        for id_vacuna in data.nuevas_vacunas:
            ev = vacuna_service.agregar_vacuna_a_esquema(
                db, esquema.id_esquema, id_vacuna, commit=False
            )
            esquemas_nuevos[id_vacuna] = ev.id_esquema_vacuna

        
        for dosis_data in data.dosis:
            if dosis_data.id_esquema_vacuna:
                id_ev = dosis_data.id_esquema_vacuna
            elif dosis_data.id_vacuna_nueva:
                id_ev = esquemas_nuevos.get(dosis_data.id_vacuna_nueva)
                if not id_ev:
                    raise HTTPException(
                        status_code=400,
                        detail=f"La vacuna {dosis_data.id_vacuna_nueva} no fue agregada en esta consulta"
                    )
            else:
                raise HTTPException(status_code=400, detail="Dosis sin vacuna asociada")

        
            from schemas.vacuna import DosisCreate
            vacuna_service.registrar_dosis(
                db=db,
                data=DosisCreate(
                    id_esquema_vacuna=id_ev,
                    fecha_aplicacion=dosis_data.fecha_aplicacion,
                    fecha_proxima_dosis=dosis_data.fecha_proxima_dosis,
                    id_consulta=consulta.id_consulta,
                ),
                id_veterinaria=id_veterinario,
                commit=False,
            )

   
    db.commit()
    db.refresh(consulta)
    return consulta

def obtener_detalle(db: Session, id_consulta: str) -> dict:
    """
    Devuelve una consulta con los tratamientos y dosis creados en ella.
 
    """
    consulta = db.query(Consulta).filter(Consulta.id_consulta == id_consulta).first()
    if not consulta:
        raise HTTPException(status_code=404, detail="Consulta no encontrada")
 

 
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
        "dosis": [
            {
                "nombre_vacuna":   nombre_vacuna,
                "numero_dosis":    d.numero_dosis,
                "fecha_aplicacion": str(d.fecha_aplicacion),
            }
            for d, nombre_vacuna in dosis
        ],
    }
 

