from fastapi import HTTPException
from sqlalchemy.orm import Session

from config.database import UsuarioTutor
from services import tutor_service, mascota_service
from schemas.mascota import MascotaResumen, ResultadoBusquedaTutor


def listar_mascotas_por_cedula(db: Session, cedula: str) -> ResultadoBusquedaTutor:
    """
    Busca un tutor por cédula exacta y retorna su nombre,
    cantidad de mascotas activas y la lista resumida de cada una.

    """
    tutor = (
        db.query(UsuarioTutor)
        .filter(UsuarioTutor.cedula == cedula)
        .first()
    )

    if not tutor:
        raise HTTPException(
            status_code=404,
            detail="No se encontró ningún tutor con esa cédula"
        )

    # reutiliza la lógica de tutor_service 
    mascotas = tutor_service.obtener_mascotas(db, tutor.id_tutor)

    
    resumenes = [
        MascotaResumen(
            id_mascota = m.id_mascota,
            nombre     = m.nombre,
            especie    = m.especie,
            foto_url   = m.foto_url,
            edad       = mascota_service.calcular_edad(m),
        )
        for m in mascotas
    ]
 
    return ResultadoBusquedaTutor(
        nombre_tutor      = tutor.nombre,
        cantidad_mascotas = len(resumenes),
        mascotas          = resumenes,
    )