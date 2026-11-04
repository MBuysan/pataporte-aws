from messaging.delivery import _generar_pdf, _enviar_pdf_por_email
import hashlib
import json
from messaging.publisher import publicar_email
from email import encoders


from datetime import datetime, timezone
from sqlalchemy.orm import Session
from fastapi import HTTPException

from config.database import (
    Mascota,
    MascotaTutor,
    UsuarioTutor,
    EsquemaVacunacion,
    TipoVacunas,
    Veterinario,
    Organizacion,
    Pataporte,
)



def generar_pataporte(db: Session, id_mascota: str, emitido_por_rol: str, emitido_por_id: str) -> Pataporte:
    """
    Genera (o actualiza) el pataporte digital de una mascota.
        - Verifica que la mascota, el veterinario emisor, su organización y el tutor existan.
        - Obtiene los datos necesarios para construir la credencial JSON.
        - Depreca cualquier pataporte vigente anterior para esa mascota.
        - Crea un nuevo registro de pataporte con estado "vigente" y fecha de emisión actual.
        - Genera el PDF del pataporte y lo envía por email al tutor.
    """
    
    mascota = (db.query(Mascota)
               .filter(Mascota.id_mascota == id_mascota)
               .first()
               )
    if not mascota:
        raise HTTPException(status_code=404, detail="Mascota no encontrada")

    
    tutor = (
        db.query(UsuarioTutor)
        .join(MascotaTutor, UsuarioTutor.id_tutor == MascotaTutor.id_tutor)
        .filter(MascotaTutor.id_mascota == id_mascota)
        .first()
        )
    if not tutor:
        raise HTTPException(status_code=400, detail="Tutor no encontrado")
    
    esquemas = (
        db.query(EsquemaVacunacion)
        .filter(EsquemaVacunacion.id_mascota == id_mascota)
        .all()
    )
    
    #deprecar pataporte vigente anterior
    db.query(Pataporte).filter(
        Pataporte.id_mascota == id_mascota,
        Pataporte.estado == "vigente",
    ).update({"estado": "deprecado"})
    
    fecha_emision = datetime.now(timezone.utc)
    
    credencial= _construir_credencial_json(
        mascota, tutor, esquemas, fecha_emision
    )
    
    hash_verificacion = _calcular_hash(credencial)

    
    nuevo_pataporte = Pataporte(
        id_mascota=id_mascota,
        emitido_por_rol=emitido_por_rol,
        emitido_por_id=emitido_por_id,
        hash_verificacion=hash_verificacion,
        credencial_json= json.dumps(credencial, ensure_ascii=False),
        estado="vigente",
        fecha_emision=fecha_emision,
    )
    
    db.add(nuevo_pataporte)
    publicar_email({
        "tipo": "pdf_email",
        "email": tutor.email,
        "nombre_mascota": mascota.nombre,
        "credencial": credencial,
        "hash_verificacion": hash_verificacion
    }, db)
    db.commit()
    db.refresh(nuevo_pataporte)
    
    
    return nuevo_pataporte



def verificar_pataporte(db: Session, hash_verificacion: str) -> dict:
    
    pataporte = (
        db.query(Pataporte)
        .filter(Pataporte.hash_verificacion == hash_verificacion)
        .first()
    )
    
    if not pataporte:
        raise HTTPException(status_code=404, detail="Pataporte no encontrado")
    
    credencial = json.loads(pataporte.credencial_json)
    subject = credencial.get("credentialSubject", {})
    
    return {
        "valido": pataporte.estado == "vigente",
        "estado": pataporte.estado,
        "fecha_emision": pataporte.fecha_emision.isoformat(),
        "mascota": {
            "nombre":   subject.get("nombre"),
            "especie":  subject.get("especie"),
            "raza":     subject.get("raza"),
            "tutor":    subject.get("tutor"),
        },
        "emisor": {
            "nombre":  "Pataporte",
        },
        "esquema_general_completo": subject.get("esquema_general_completo"),
        "vacunas": subject.get("vacunas", []),
    }
        
    

#----------------funciones privadas--------------------------


def _construir_credencial_json(mascota: Mascota, tutor: UsuarioTutor, esquemas: list, fecha_emision: datetime) -> dict:
    
    """
    Construye la estructura de la credencial JSON del pataporte digital, incluyendo:
    - Datos de identidad de la mascota (nombre, especie, raza, fecha de nacimiento, sexo).
    - Datos del tutor principal (nombre, cédula).
    - Datos del veterinario emisor (nombre, matrícula) y su organización (nombre).
    - Esquemas de vacunación con sus vacunas, dosis aplicadas (número, fecha, veterinario aplicador) y estado de esquema (completo/incompleto).
    """
    
    
    vacunas_snapshot = []
    for esquema in esquemas:
        for ev in esquema.vacunas:
            tipo: TipoVacunas = ev.tipo_vacuna
            dosis_lista = sorted(ev.dosis, key=lambda d: d.numero_dosis)
            dosis_snapshot = []
            
            for d in dosis_lista:
                vet_aplicador: Veterinario = d.veterinario
                org_aplicador: Organizacion = vet_aplicador.organizacion if vet_aplicador else None
                dosis_snapshot.append({
                    "numero": d.numero_dosis,
                    "fecha": str(d.fecha_aplicacion),
                    "veterinario_aplicador": {
                        "nombre": vet_aplicador.nombre if vet_aplicador else None,
                        "matricula": vet_aplicador.matricula if vet_aplicador else None,
                        "organizacion_rut": org_aplicador.rut if org_aplicador else None,
                    }
                })
                
            esquema_completo = (len(dosis_lista) >= tipo.cantidad_dosis_requeridas)
                
            vacunas_snapshot.append({
                "nombre": tipo.nombre,
                "descripcion": tipo.descripcion,
                "dosis_requeridas": tipo.cantidad_dosis_requeridas,
                "dosis_aplicadas": dosis_snapshot,
                "esquema_completo": esquema_completo,
            })
                
    esquema_general_completo = (
        all(v["esquema_completo"] for v in vacunas_snapshot)
        if vacunas_snapshot else False
    )
                
                
    return {
            "@context": ["https://www.w3.org/2018/credentials/v1"],
            "type": ["CredencialVerificable", "PataporteMascota"],
            "issuanceDate": fecha_emision.isoformat(),
            "issuer": {
                "id":     "urn:sistema:pataporte",
                "nombre": "Pataporte",
            },
            "credentialSubject": {
                "id":               f"urn:mascota:{mascota.id_mascota}",
                "nombre":           mascota.nombre,
                "especie":          mascota.especie,
                "raza":             mascota.raza,
                "fecha_nacimiento": str(mascota.fecha_de_nacimiento) if mascota.fecha_de_nacimiento else None,
                "sexo":             mascota.sexo,
                "tutor": {
                    "nombre": tutor.nombre if tutor else None,
                    "cedula": tutor.cedula if tutor else None,
                },
                "vacunas":                    vacunas_snapshot,
                "esquema_general_completo":   esquema_general_completo,
            },
        }
                
def _calcular_hash(credencial: dict) -> str:
    
    """
    genera un hash SHA-256 a partir del contenido de la credencial JSON, 
    para usarlo como mecanismo de verificación de integridad y autenticidad del pataporte digital.
    """

    contenido = json.dumps(credencial, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(contenido.encode('utf-8')).hexdigest()
