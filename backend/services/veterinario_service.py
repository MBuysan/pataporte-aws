from fastapi import HTTPException
from sqlalchemy.orm import Session

from config.database import UsuarioTutor, Veterinario
from services import tutor_service, mascota_service
from schemas.mascota import MascotaResumen, ResultadoBusquedaTutor


def buscar_por_cedula(db: Session, cedula: str) -> ResultadoBusquedaTutor:
    """
    busca un tutor por cédula exacta y devuelve su nombre
    junto con la lista completa de sus mascotas activas.
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

    mascotas = tutor_service.obtener_mascotas(db, tutor.id_tutor)

    return ResultadoBusquedaTutor(
        nombre_tutor = tutor.nombre,
        mascotas     = [
            MascotaResumen(
                id_mascota = m.id_mascota,
                nombre     = m.nombre,
                especie    = m.especie,
                foto_url   = m.foto_url,
                edad       = mascota_service.calcular_edad(m),
            )
            for m in mascotas
        ],
    )


def registrar_veterinaria(db: Session, vet_data) -> Veterinario:
    from services.auth_service import _hashear, generar_y_enviar_codigo_verificacion
    
    # Validar que no exista el rut o el email
    existente = db.query(Veterinario).filter(
        (Veterinario.rut == vet_data.rut) | (Veterinario.email == vet_data.email)
    ).first()
    
    if existente:
        if existente.rut == vet_data.rut:
            raise HTTPException(status_code=400, detail="El RUT ya está registrado")
        if existente.email == vet_data.email:
            raise HTTPException(status_code=400, detail="El correo electrónico ya está registrado")

    # Crear Veterinario (Organización) en estado pendiente_verificacion
    nueva_vet = Veterinario(
        rut=vet_data.rut,
        nombre=vet_data.nombre,
        email=vet_data.email,
        password_hash=_hashear(vet_data.password),
        estado="pendiente_verificacion"
    )
    db.add(nueva_vet)
    db.commit()
    db.refresh(nueva_vet)



    # Generamos el código de verificación y lo enviamos por correo
    generar_y_enviar_codigo_verificacion(db, nueva_vet.email, "veterinario")
    
    return nueva_vet