from typing import Optional
import uuid
import hashlib
from datetime import date, timedelta
from sqlalchemy.orm import Session
from fastapi import HTTPException

from schemas.vacuna import DosisCreate
from config.database import Dosis, EsquemaVacunacion, EsquemaVacuna, Mascota, TipoVacunas

def crear_esquema(db: Session, id_mascota: str):
    
    mascota = db.query(Mascota).filter_by(
        id_mascota=id_mascota).first()
    
    if mascota.especie not in ["perro", "gato"]:
        raise HTTPException(
            status_code=400,
            detail="La mascota debe ser perro o gato para crear un esquema de vacunación"
        )
    
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

def agregar_vacuna_a_esquema(db: Session, id_esquema: str, id_vacuna: str, commit: bool = True):

    esquema = db.query(EsquemaVacunacion).filter_by(
        id_esquema=id_esquema
    ).first()

    if not esquema:
        raise HTTPException(status_code=404, detail="Esquema no existe")
    
    mascota = esquema.mascota
    

    vacuna = db.query(TipoVacunas).filter_by(
        id_vacuna=id_vacuna
    ).first()

    if not vacuna:
        raise HTTPException(status_code=404, detail="Vacuna no existe")
    
    if vacuna.especie_objetivo != mascota.especie:
        raise HTTPException(
            status_code=400,
            detail=f"La vacuna no es compatible con la especie de la mascota ({mascota.especie})"
        )

    if vacuna.especie_objetivo != mascota.especie:
        raise HTTPException(
            status_code=400,
            detail=f"La vacuna no es compatible con la especie de la mascota ({mascota.especie})"
        )

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
    db.flush()
    
    if commit:
        db.commit()
        db.refresh(esquema_vacuna)

    return esquema_vacuna

def registrar_dosis(db: Session, data: DosisCreate, id_veterinario: str, commit: bool = True):
    esquema_vacuna = db.query(EsquemaVacuna).filter_by(
        id_esquema_vacuna=data.id_esquema_vacuna
    ).first()

    if not esquema_vacuna:
        raise HTTPException(status_code=404, detail="Vacuna no encontrada en el esquema")

    # contar dosis ya aplicadas para esta vacuna en el esquema
    cantidad_actual = db.query(Dosis).filter_by(
        id_esquema_vacuna=data.id_esquema_vacuna
    ).count()
    
    tipo_vacuna = esquema_vacuna.tipo_vacuna

    if cantidad_actual >= tipo_vacuna.cantidad_dosis_requeridas:
        raise HTTPException(
            status_code=400,
            detail="El esquema de vacunación ya está completo para esta vacuna"
        )

    dosis = Dosis(
        id_dosis=str(uuid.uuid4()),
        id_esquema_vacuna=data.id_esquema_vacuna,
        id_veterinario=id_veterinario,
        id_consulta=data.id_consulta,
        numero_dosis=cantidad_actual + 1,  # Número calculado automáticamente
        fecha_aplicacion=data.fecha_aplicacion,
 
    )

    db.add(dosis)
    db.flush()

    
    _actualizar_proxima_dosis(db, dosis, data.fecha_proxima_dosis)

    if commit:
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
            
            cantidad_dosis_aplicadas = len(dosis)
            
            cantidad_dosis_requeridas = tipo.cantidad_dosis_requeridas
            
            dosis_restantes = max(0, cantidad_dosis_requeridas - cantidad_dosis_aplicadas)

            vacunas_response.append({
                "id_esquema_vacuna": ev.id_esquema_vacuna,
                "id_vacuna": ev.id_vacuna,
                "nombre": tipo.nombre if tipo else "Sin nombre",
                "estado": ev.estado,
                "fecha_inicio": esquema.fecha_inicio,
                "fecha_proxima_dosis": ev.fecha_proxima_dosis,
                "dosis": dosis,
                "dosis_aplicadas": cantidad_dosis_aplicadas,
                "dosis_requeridas": cantidad_dosis_requeridas,
                "dosis_restantes": dosis_restantes
            })

        resultado.append({
            "id_esquema": esquema.id_esquema,
            "id_mascota": esquema.id_mascota,
            "vacunas": vacunas_response
        })

    return resultado





def _actualizar_proxima_dosis(db: Session, dosis: Dosis, fecha_proxima_dosis: Optional[date]):
    
    esquema_vacuna = dosis.esquema_vacuna
    tipo_vacuna = esquema_vacuna.tipo_vacuna

    cantidad_actual = db.query(Dosis).filter_by(
        id_esquema_vacuna=esquema_vacuna.id_esquema_vacuna
    ).count()
    
    
    if (
        fecha_proxima_dosis is not None
        and fecha_proxima_dosis <= dosis.fecha_aplicacion
    ):
        raise HTTPException(
            status_code=400,
            detail="La fecha de la próxima dosis debe ser posterior"
        )


    if cantidad_actual >= tipo_vacuna.cantidad_dosis_requeridas:
        
        esquema_vacuna.estado = "completado"
        esquema_vacuna.fecha_proxima_dosis = None
        
        db.add(esquema_vacuna)
        return

    

    if fecha_proxima_dosis is not None:
        
        esquema_vacuna.fecha_proxima_dosis = fecha_proxima_dosis
    
    elif tipo_vacuna.intervalo_entre_dosis_dias is not None:
        
        esquema_vacuna.fecha_proxima_dosis = dosis.fecha_aplicacion + timedelta(days=tipo_vacuna.intervalo_entre_dosis_dias)
    
    else:
        
        esquema_vacuna.fecha_proxima_dosis = None
        
    
    esquema_vacuna.estado = "activo"
    

    db.add(esquema_vacuna)

def editar_esquema_vacuna(
    db: Session,
    id_esquema_vacuna: str,
    agregar_dosis: list[DosisCreate] = None,
    eliminar_dosis: list[str] = None,
    id_veterinario: str = None
):

    esquema_vacuna = db.query(EsquemaVacuna).filter_by(
        id_esquema_vacuna=id_esquema_vacuna
    ).first()

    if not esquema_vacuna:
        raise HTTPException(
            status_code=404,
            detail="Esquema vacuna no encontrado"
        )

    # -------------------------
    # ELIMINAR DOSIS
    # -------------------------
    if eliminar_dosis:

        dosis_existentes = (
            db.query(Dosis)
            .filter(
                Dosis.id_dosis.in_(eliminar_dosis),
                Dosis.id_esquema_vacuna == id_esquema_vacuna
            )
            .all()
        )

        for dosis in dosis_existentes:
            db.delete(dosis)

        db.flush()

        # Reordenar números de dosis
        dosis_restantes = (
            db.query(Dosis)
            .filter_by(id_esquema_vacuna=id_esquema_vacuna)
            .order_by(Dosis.fecha_aplicacion.asc())
            .all()
        )

        for index, dosis in enumerate(dosis_restantes, start=1):
            dosis.numero_dosis = index

    # -------------------------
    # AGREGAR DOSIS
    # -------------------------
    if agregar_dosis:

        cantidad_actual = db.query(Dosis).filter_by(
            id_esquema_vacuna=id_esquema_vacuna
        ).count()

        for nueva in agregar_dosis:

            tipo_vacuna = esquema_vacuna.tipo_vacuna
            
            if cantidad_actual >= tipo_vacuna.cantidad_dosis_requeridas:
                raise HTTPException(
                    status_code=400,
                    detail="No se pueden agregar más dosis, el esquema ya está completo para esta vacuna"
                )
            
            cantidad_actual += 1

            dosis = Dosis(
                id_dosis=str(uuid.uuid4()),
                id_esquema_vacuna=id_esquema_vacuna,
                id_veterinario=id_veterinario,
                id_consulta=nueva.id_consulta,
                numero_dosis=cantidad_actual,
                fecha_aplicacion=nueva.fecha_aplicacion,
            )

            db.add(dosis)
            db.flush()

            
            _actualizar_proxima_dosis(db, dosis, nueva.fecha_proxima_dosis)

    # -------------------------
    # RECALCULAR ESTADO
    # -------------------------
    total_dosis = db.query(Dosis).filter_by(
        id_esquema_vacuna=id_esquema_vacuna
    ).count()

    tipo_vacuna = esquema_vacuna.tipo_vacuna

    if total_dosis >= tipo_vacuna.cantidad_dosis_requeridas:
        esquema_vacuna.estado = "completado"
        esquema_vacuna.fecha_proxima_dosis = None
    else:
        esquema_vacuna.estado = "activo"


    db.add(esquema_vacuna)

    db.commit()
    db.refresh(esquema_vacuna)

    return esquema_vacuna

def obtener_tipos_vacuna(db: Session, especie: Optional[str] = None):
    
    query = db.query(TipoVacunas).filter(
        TipoVacunas.activo == True
    )

    if especie:
        
        query = query.filter(
            TipoVacunas.especie_objetivo == especie
        )

    return query.all()