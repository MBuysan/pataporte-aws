import secrets
import string
import smtplib
import os
from io import BytesIO
from datetime import date, datetime, timedelta, timezone
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException

from config.settings import settings
from schemas.mascota import MascotaCreate, MascotaUpdate
from config.database import Mascota, CodigoAccesoMascota, UsuarioTutor, MascotaTutor

from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from reportlab.pdfgen import canvas

def listar(db: Session):
    return db.query(Mascota).filter(Mascota.estado == "activo").all()


def obtener_por_id(db: Session, id_mascota: str):
    return db.query(Mascota).filter(Mascota.id_mascota == id_mascota).first()


def crear(db: Session, data: MascotaCreate):
    """
    *Funcionalidad:*
    Crear una nueva mascota con id único generado por el sistema y asociarlo con el tutor

    *Retorna:*
    nueva_mascota[obj]

    *Validaciones:*
        1) Valida si existe el tutor, en caso de que no, lanza excepción 404
        2) Valida si existe actualmente una mascota con el mismo: nombre, especie y feha de nacimiento para ese tutor, en caso de que no, lanza excepción 409
        3) Si por cualquier motivo el sistema no consigue almacenar la nueva mascota y su relacion con el tutor en la base de datos, lanza excepción 500

    *Información adicional:*

    .add() -> añade a la BD

    .flush() -> borra el buffer interno y fuerza a que todos los datos que el dato almacenado se escriba inmediatamente en su destino

    """
    tutor = (
        db.query(UsuarioTutor).filter(UsuarioTutor.id_tutor == data.id_tutor).first()
    )
    if not tutor:
        raise HTTPException(status_code=404, detail="Tutor no encontrado")

    duplicado = (
        db.query(Mascota)
        .join(MascotaTutor, Mascota.id_mascota == MascotaTutor.id_mascota)
        .filter(
            MascotaTutor.id_tutor == data.id_tutor,
            Mascota.nombre == data.nombre,
            Mascota.especie == data.especie,
            Mascota.fecha_de_nacimiento == data.fecha_de_nacimiento,
        )
        .first()
    )
    if duplicado:
        raise HTTPException(
            status_code=409,
            detail="Ya existe una mascota con ese nombre, especie y fecha de nacimiento para este tutor",
        )
        
    if data.fecha_de_nacimiento and data.fecha_de_nacimiento > date.today():
        raise HTTPException(
            status_code=400,
            detail="La fecha de nacimiento no puede ser futura"
        )

    nueva_mascota = Mascota(
        nombre=data.nombre,
        especie=data.especie,
        raza=data.raza,
        fecha_de_nacimiento=data.fecha_de_nacimiento,
        sexo=data.sexo,
        foto_url=data.foto_url,
    )

    db.add(nueva_mascota)
    db.flush()

    vinculo_mascota_tutor = MascotaTutor(
        id_tutor=data.id_tutor,
        id_mascota=nueva_mascota.id_mascota,
        rol_tutor="principal",
    )
    db.add(vinculo_mascota_tutor)

    try:
        db.commit()
        db.refresh(nueva_mascota)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=500, detail="Error al registrar la mascota")

    return nueva_mascota


def calcular_edad(mascota) -> int | None:
    """
    calcula la edad en años a partir de la fecha de nacimiento.
    devuelve none si la mascota no tiene fecha de nacimiento registrada.
 
    """
    if not mascota.fecha_de_nacimiento:
        return None
    hoy = date.today()
    # resta 1 si todavía no llegó el cumpleaños este año
    return (
        hoy.year - mascota.fecha_de_nacimiento.year
        - ((hoy.month, hoy.day) < (mascota.fecha_de_nacimiento.month, mascota.fecha_de_nacimiento.day))
    )



def generar_codigo_acceso(db: Session, id_mascota: str):
    """
    Genera un código único de 8 caracteres para compartir acceso.
    Expira en 24 horas.
    """
    mascota = obtener_por_id(db, id_mascota)
    if not mascota:
        raise HTTPException(status_code=404, detail="Mascota no encontrada")

    # Generar código alfanumérico aleatorio
    caracteres = string.ascii_uppercase + string.digits
    codigo = "".join(secrets.choice(caracteres) for _ in range(8))

    # Definir expiración (24 horas)
    expiracion = datetime.now(timezone.utc) + timedelta(hours=24)

    nuevo_codigo = CodigoAccesoMascota(
        id_mascota=id_mascota, codigo=codigo, fecha_expiracion=expiracion
    )

    db.add(nuevo_codigo)
    try:
        db.commit()
        db.refresh(nuevo_codigo)
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500, detail=f"Error al generar el código: {str(e)}"
        )

    return nuevo_codigo



def eliminar(db: Session, id_mascota: str, id_tutor: str):
    mascota = (
        db.query(Mascota)
        .join(MascotaTutor)
        .filter(
            Mascota.id_mascota == id_mascota,
            Mascota.estado == "activo",
            MascotaTutor.id_tutor == id_tutor,
        )
        .first()
    )

    if not mascota:
        raise HTTPException(
            status_code=404,
            detail="Mascota no encontrada o sin permisos"
        )

    _enviar_historial_por_email(db, mascota)

    try:
        db.delete(mascota)
        db.commit()

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"No se pudo eliminar la mascota: {str(e)}"
        )

def _enviar_historial_por_email(db: Session, mascota):
    tutor = (
        db.query(UsuarioTutor)
        .join(MascotaTutor)
        .filter(
            MascotaTutor.id_mascota == mascota.id_mascota,
            MascotaTutor.rol_tutor == "principal",
        )
        .first()
    )

    if not tutor:
        raise HTTPException(status_code=404, detail="Tutor principal no encontrado")

    pdf_buffer = BytesIO()
    pdf = canvas.Canvas(pdf_buffer)
    y = 800

    def salto_pagina_si_necesita():
        nonlocal y
        if y < 80:
            pdf.showPage()
            y = 800
            pdf.setFont("Helvetica", 10)

    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(50, y, f"Historial clínico de {mascota.nombre}")
    y -= 40

    pdf.setFont("Helvetica", 11)
    pdf.drawString(50, y, f"Especie: {mascota.especie}")
    y -= 20
    pdf.drawString(50, y, f"Raza: {mascota.raza or 'No registrada'}")
    y -= 20
    pdf.drawString(50, y, f"Fecha de registro: {mascota.fecha_registro}")
    y -= 40

    # CONSULTAS
    pdf.setFont("Helvetica-Bold", 13)
    pdf.drawString(50, y, "Consultas:")
    y -= 25

    pdf.setFont("Helvetica", 10)

    if mascota.consultas:
        for consulta in mascota.consultas:
            salto_pagina_si_necesita()
            pdf.drawString(60, y, f"- {consulta.fecha_hora.date()} | {consulta.motivo}")
            y -= 18

            if consulta.diagnostico:
                salto_pagina_si_necesita()
                pdf.drawString(75, y, f"Diagnóstico: {consulta.diagnostico}")
                y -= 18

            if consulta.tratamiento_indicado:
                salto_pagina_si_necesita()
                pdf.drawString(75, y, f"Tratamiento indicado: {consulta.tratamiento_indicado}")
                y -= 18
    else:
        pdf.drawString(60, y, "Sin consultas registradas")
        y -= 20

    y -= 20

    # TRATAMIENTOS
    pdf.setFont("Helvetica-Bold", 13)
    pdf.drawString(50, y, "Tratamientos:")
    y -= 25

    pdf.setFont("Helvetica", 10)

    if mascota.tratamientos:
        for tratamiento in mascota.tratamientos:
            salto_pagina_si_necesita()
            pdf.drawString(60, y, f"- {tratamiento.nombre}")
            y -= 18

            if tratamiento.descripcion:
                salto_pagina_si_necesita()
                pdf.drawString(75, y, f"Descripción: {tratamiento.descripcion}")
                y -= 18

            if tratamiento.frecuencia:
                salto_pagina_si_necesita()
                pdf.drawString(75, y, f"Frecuencia: {tratamiento.frecuencia}")
                y -= 18
    else:
        pdf.drawString(60, y, "Sin tratamientos registrados")
        y -= 20

    y -= 20

    # VACUNAS
    salto_pagina_si_necesita()
    pdf.setFont("Helvetica-Bold", 13)
    pdf.drawString(50, y, "Vacunas:")
    y -= 25

    pdf.setFont("Helvetica", 10)

    hay_vacunas = False

    for esquema in mascota.esquemas:
        for esquema_vacuna in esquema.vacunas:
            hay_vacunas = True

            nombre_vacuna = (
                esquema_vacuna.tipo_vacuna.nombre
                if esquema_vacuna.tipo_vacuna
                else "Vacuna sin nombre"
            )

            salto_pagina_si_necesita()
            pdf.drawString(60, y, f"- {nombre_vacuna} | Estado: {esquema_vacuna.estado}")
            y -= 18

            if esquema_vacuna.fecha_proxima_dosis:
                salto_pagina_si_necesita()
                pdf.drawString(75, y, f"Próxima dosis: {esquema_vacuna.fecha_proxima_dosis}")
                y -= 18

            if esquema_vacuna.dosis:
                for dosis in esquema_vacuna.dosis:
                    salto_pagina_si_necesita()
                    pdf.drawString(
                        75,
                        y,
                        f"Dosis {dosis.numero_dosis} aplicada el {dosis.fecha_aplicacion}"
                    )
                    y -= 18
            else:
                salto_pagina_si_necesita()
                pdf.drawString(75, y, "Sin dosis aplicadas")
                y -= 18

    if not hay_vacunas:
        pdf.drawString(60, y, "Sin vacunas registradas")
        y -= 20

    # GUARDAR PDF
    pdf.save()
    pdf_buffer.seek(0)

    # EMAIL
    mensaje = MIMEMultipart()
    mensaje["Subject"] = f"Respaldo clínico de {mascota.nombre}"
    mensaje["From"] = settings.MAIL_FROM
    mensaje["To"] = tutor.email

    cuerpo = f"""
Hola,

Adjuntamos el respaldo clínico de {mascota.nombre}
previo a la eliminación definitiva de su perfil en Pataporte.

Equipo Pataporte
"""

    mensaje.attach(MIMEText(cuerpo, "plain", "utf-8"))

    adjunto = MIMEApplication(pdf_buffer.read(), _subtype="pdf")
    adjunto.add_header(
        "Content-Disposition",
        "attachment",
        filename=f"historial_{mascota.nombre}.pdf"
    )

    mensaje.attach(adjunto)

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as servidor:
            servidor.login(settings.MAIL_USERNAME, settings.MAIL_PASSWORD)
            servidor.sendmail(settings.MAIL_FROM, tutor.email, mensaje.as_string())

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"No se pudo enviar el respaldo: {str(e)}"
        )