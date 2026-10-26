from utils.auth import get_current_user, get_current_vet, get_current_tutor, require_tutor, require_pet_access
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from typing import Optional
import uuid, os, shutil
from sqlalchemy.orm import Session

from config.database import get_db
from schemas.mascota import (
    MascotaCreate,
    MascotaResponse,
    CodigoAccesoResponse,
    EspecieEnum,
    SexoEnum
)
from services import mascota_service
from utils import password_utils

UPLOAD_DIR = "uploads/mascotas"
os.makedirs(UPLOAD_DIR, exist_ok=True)


# todos las etiquetas get,post etc de mas abajo se registran sobre este objeto
"""
parametros dentro del endpoint
1er parametro: permite agregar entre llaves un parametro de ruta, usualmente es usado mas adelante en el flujo
2do parametro: le dice lo que espera del retorno, puede ser una forma de objeto especifica del schema, o una lista de los mismos
3er parametro: summary (resumen) o description usualmente
"""
router = APIRouter(dependencies=[Depends(get_current_user)])

@router.get(
    "/", response_model=list[MascotaResponse], summary="Listar todas las mascotas"
)
def listar_mascotas(db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    if user["rol"] == "tutor":
        from services.tutor_service import obtener_mascotas
        return obtener_mascotas(db, user["id"])
    return mascota_service.listar(db)


@router.get("/{id_mascota}", response_model=MascotaResponse, summary="Obtener mascota")
def obtener_mascota(id_mascota: str, db: Session = Depends(get_db), user: dict = Depends(get_current_user)):
    mascota = require_pet_access(db, id_mascota, user)
    if not mascota:
        raise HTTPException(status_code=404, detail="Mascota no encontrada")
    return mascota


@router.post(
    "/", response_model=MascotaResponse, status_code=201, summary="Registrar mascota"
)
async def registrar_mascota( #por como se reciben los datos, se debe usar async y Form para cada uno de los campos (cuestiones el protocolo multipart/form-data)
    id_tutor: str = Form(...),
    nombre: str = Form(...),
    especie: str = Form(...),
    raza: Optional[str] = Form(None),
    fecha_de_nacimiento: Optional[str] = Form(None),
    sexo: str = Form("desconocido"),
    foto: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    user: dict = Depends(require_tutor),
):
    if id_tutor != user["id"]:
        raise HTTPException(status_code=403, detail="No autorizado")
    foto_url = None

    if foto and foto.filename:
        extension = foto.filename.split(".")[-1].lower()
        if extension not in ["jpg", "jpeg", "png", "webp"]:
            raise HTTPException(status_code=400, detail="Formato de imagen no permitido")

        nombre_archivo = f"{uuid.uuid4()}.{extension}"
        ruta_guardado = f"{UPLOAD_DIR}/{nombre_archivo}"

        with open(ruta_guardado, "wb") as buffer:
            shutil.copyfileobj(foto.file, buffer)

        # url pública que queda guardada en postgres
        foto_url = f"/uploads/mascotas/{nombre_archivo}"


    data = MascotaCreate(
        id_tutor=id_tutor,
        nombre=nombre,
        especie=EspecieEnum(especie),
        raza=raza or None,
        fecha_de_nacimiento=fecha_de_nacimiento or None,
        sexo=SexoEnum(sexo),
        foto_url=foto_url,
    )

    return mascota_service.crear(db, data)



@router.delete("/{id_mascota}", status_code=204, summary="Eliminar mascota")
def eliminar_mascota(
    id_mascota: str,
    db: Session = Depends(get_db),
    id_tutor: str = Depends(get_current_tutor),
):
    mascota_service.eliminar(db, id_mascota, id_tutor)


@router.post(
    "/{id_mascota}/generar-codigo",
    response_model=CodigoAccesoResponse,
    summary="Generar código para compartir",
)
def generar_codigo(id_mascota: str, db: Session = Depends(get_db), user: dict = Depends(require_tutor)):
    require_pet_access(db, id_mascota, user)
    return mascota_service.generar_codigo_acceso(db, id_mascota)
