from fastapi import HTTPException
from sqlalchemy.orm import Session

from services.auth_service import _hashear, generar_y_enviar_codigo_verificacion
from config.database import UsuarioTutor, Veterinario, Organizacion
from services import tutor_service, mascota_service
from schemas.mascota import MascotaResumen, ResultadoBusquedaTutor
from schemas.veterinario import VeterinarioCreate

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



def registrar_veterinario(db: Session, vet_data: VeterinarioCreate) -> Veterinario:
    
    
    # Validar que no exista el email
    existente_email = db.query(Veterinario).filter(
        Veterinario.email == vet_data.email
        ).first()
    if existente_email:
        raise HTTPException(status_code=400, detail="El correo electrónico ya está registrado")
    
    existente_matricula = db.query(Veterinario).filter(
        Veterinario.matricula == vet_data.matricula
        ).first()
    if existente_matricula:
        raise HTTPException(status_code=400, detail="La matrícula ya está registrada")
    
    organizacion = _obtener_o_crear_organizacion(db, vet_data.rut_organizacion)

    # Crear Veterinario asociado a esa organización 
    nuevo_vet = Veterinario(
        id_organizacion=organizacion.id_organizacion,
        matricula=vet_data.matricula,
        nombre=vet_data.nombre,
        email=vet_data.email,
        password_hash=_hashear(vet_data.password),
        estado="pendiente_verificacion"
    )
    db.add(nuevo_vet)
    db.flush()
    generar_y_enviar_codigo_verificacion(db, nuevo_vet.email, "veterinario", commit=False)
    db.commit()
    db.refresh(nuevo_vet)


    
    return nuevo_vet

def _obtener_o_crear_organizacion(db: Session, rut: str) -> Organizacion:
    
    org = db.query(Organizacion).filter(Organizacion.rut == rut).first()
    if org:
        return org
 
    nueva_org = Organizacion(
        rut=rut
        )
    db.add(nueva_org)
    db.flush()  
    return nueva_org
