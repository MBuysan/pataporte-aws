from utils.email import enviar_email
import hashlib
import io
import json
from messaging.publisher import publicar_email
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable

from datetime import datetime, timezone
from config.settings import settings
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
    db.commit()
    db.refresh(nuevo_pataporte)
    
    
    try: 
        publicar_email({
            "tipo": "pdf_email",
            "email": tutor.email,
            "nombre_mascota": mascota.nombre,
            "credencial": credencial,
            "hash_verificacion": hash_verificacion
        })
    except Exception as e:
        print(f"Error al generar/enviar PDF: {e}")
    
    
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



def _generar_pdf(credencial: dict, hash_verificacion: str) -> bytes:
    
    """
    genera un PDF con el diseño del pataporte digital, incluyendo:
    - Encabezado con el título "Pataporte" y fecha de emisión.
    - Sección de datos de la mascota (nombre, especie, raza, fecha de nacimiento, sexo).
    - Sección de datos del tutor (nombre, cédula).
    - Sección de vacunación, listando cada vacuna con su estado (completo/incompleto) y detalle de dosis aplicadas (número, fecha, veterinario aplicador).
    - Código de verificación (hash) al final del documento para permitir su autenticación.
    """
    
    
    
    buffer = io.BytesIO()
 
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=2.5 * cm,
        rightMargin=2.5 * cm,
        topMargin=2.5 * cm,
        bottomMargin=2.5 * cm,
    )
 
    W = A4[0] - 5 * cm  # ancho útil
 
    base   = getSampleStyleSheet()
    AZUL   = colors.HexColor("#2563EB")
    GRIS   = colors.HexColor("#6B7280")
    VERDE  = colors.HexColor("#16A34A")
    AMARILLO = colors.HexColor("#D97706")
    NEGRO  = colors.HexColor("#111827")
    FONDO  = colors.HexColor("#F3F4F6")
 
    def estilo(name, **kw):
        s = ParagraphStyle(name, parent=base["Normal"], **kw)
        return s
 
    sty_titulo     = estilo("titulo",     fontSize=22, textColor=AZUL,  leading=26, alignment=TA_CENTER, fontName="Helvetica-Bold")
    sty_subtitulo  = estilo("subtitulo",  fontSize=10, textColor=GRIS,  leading=14, alignment=TA_CENTER)
    sty_seccion    = estilo("seccion",    fontSize=9,  textColor=GRIS,  leading=12, spaceBefore=14, fontName="Helvetica-Bold", textTransform="uppercase")
    sty_campo_lbl  = estilo("campo_lbl",  fontSize=8,  textColor=GRIS,  leading=11)
    sty_campo_val  = estilo("campo_val",  fontSize=11, textColor=NEGRO, leading=14, fontName="Helvetica-Bold")
    sty_vacuna_nom = estilo("vac_nom",    fontSize=10, textColor=NEGRO, leading=13, fontName="Helvetica-Bold")
    sty_vacuna_sub = estilo("vac_sub",    fontSize=8,  textColor=GRIS,  leading=11)
    sty_dosis_row  = estilo("dosis_row",  fontSize=9,  textColor=NEGRO, leading=12)
    sty_hash       = estilo("hash",       fontSize=7,  textColor=GRIS,  leading=10, alignment=TA_CENTER, fontName="Courier")
    sty_footer     = estilo("footer",     fontSize=8,  textColor=GRIS,  leading=11, alignment=TA_CENTER)
    sty_completo   = estilo("completo",   fontSize=10, textColor=VERDE, leading=13, fontName="Helvetica-Bold", alignment=TA_CENTER)
    sty_incompleto = estilo("incomp",     fontSize=10, textColor=AMARILLO, leading=13, fontName="Helvetica-Bold", alignment=TA_CENTER)
 
    subj   = credencial["credentialSubject"]
    vacunas = subj.get("vacunas", [])
    fecha_emision = credencial.get("issuanceDate", "")[:10]
    general_completo = subj.get("esquema_general_completo", False)
 
    story = []
 
    # ── Encabezado ────────────────────────────────────────────────────────────
    story.append(Paragraph("Pataporte", sty_titulo))
    story.append(Spacer(1, 4))
    story.append(Paragraph("Certificado de Vacunación", sty_subtitulo))
    story.append(Spacer(1, 4))
    story.append(Paragraph(f"Emitido el {fecha_emision}", sty_subtitulo))
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width=W, thickness=1, color=AZUL, spaceAfter=10))
 
    # ── Datos de la mascota ───────────────────────────────────────────────────
    story.append(Paragraph("Datos de la mascota", sty_seccion))
    story.append(Spacer(1, 6))
 
    def fila_dato(label, value):
        return [Paragraph(label, sty_campo_lbl), Paragraph(str(value) if value else "—", sty_campo_val)]
 
    tabla_mascota = Table(
        [
            fila_dato("Nombre",          subj.get("nombre")),
            fila_dato("Especie",         subj.get("especie", "").capitalize()),
            fila_dato("Raza",            subj.get("raza")),
            fila_dato("Sexo",            subj.get("sexo")),
            fila_dato("Fecha nacimiento", subj.get("fecha_nacimiento")),
        ],
        colWidths=[4 * cm, W - 4 * cm],
    )
    tabla_mascota.setStyle(TableStyle([
        ("VALIGN",      (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING",  (0, 0), (-1, -1), 0),
    ]))
    story.append(tabla_mascota)
 
    # ── Datos del tutor ───────────────────────────────────────────────────────
    tutor = subj.get("tutor", {})
    if tutor.get("nombre"):
        story.append(Spacer(1, 6))
        story.append(HRFlowable(width=W, thickness=0.5, color=FONDO, spaceAfter=6))
        story.append(Paragraph("Tutor", sty_seccion))
        story.append(Spacer(1, 6))
        tabla_tutor = Table(
            [
                fila_dato("Nombre",  tutor.get("nombre")),
                fila_dato("Cédula",  tutor.get("cedula")),
            ],
            colWidths=[4 * cm, W - 4 * cm],
        )
        tabla_tutor.setStyle(TableStyle([
            ("VALIGN",       (0, 0), (-1, -1), "TOP"),
            ("BOTTOMPADDING",(0, 0), (-1, -1), 5),
            ("TOPPADDING",   (0, 0), (-1, -1), 0),
        ]))
        story.append(tabla_tutor)
 
    # ── Vacunas ───────────────────────────────────────────────────────────────
    story.append(Spacer(1, 6))
    story.append(HRFlowable(width=W, thickness=0.5, color=FONDO, spaceAfter=6))
    story.append(Paragraph("Esquema de vacunación", sty_seccion))
    story.append(Spacer(1, 8))
 
    for vac in vacunas:
        badge = "Esquema completo" if vac["esquema_completo"] else "Esquema incompleto"
        badge_sty = sty_completo if vac["esquema_completo"] else sty_incompleto
 
        encabezado_vac = Table(
            [[Paragraph(vac["nombre"], sty_vacuna_nom), Paragraph(badge, badge_sty)]],
            colWidths=[W * 0.55, W * 0.45],
        )
        encabezado_vac.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN",  (1, 0), (1, 0),   "RIGHT"),
        ]))
        story.append(encabezado_vac)
 
        if vac.get("descripcion"):
            story.append(Paragraph(vac["descripcion"], sty_vacuna_sub))
 
        story.append(Spacer(1, 5))
 
        dosis_lista = vac.get("dosis_aplicadas", [])
        if dosis_lista:
            encabezado_tabla = [
                Paragraph("Dosis", sty_campo_lbl),
                Paragraph("Fecha", sty_campo_lbl),
                Paragraph("Veterinario",  sty_campo_lbl),
                Paragraph("Matrícula",    sty_campo_lbl),
                Paragraph("Org. (RUT)",   sty_campo_lbl),
            ]
            filas_dosis = [encabezado_tabla]
            for d in dosis_lista:
                vet_ap = d.get("veterinario_aplicador", {})
                filas_dosis.append([
                    Paragraph(f"#{d['numero']}", sty_dosis_row),
                    Paragraph(str(d.get("fecha", "—")), sty_dosis_row),
                    Paragraph(vet_ap.get("nombre") or "—", sty_dosis_row),
                    Paragraph(vet_ap.get("matricula") or "—", sty_dosis_row),
                    Paragraph(vet_ap.get("organizacion_rut") or "—", sty_dosis_row),
                ])
 
            col_w = [1.2*cm, 2.5*cm, (W-8.2*cm), 2.5*cm, 2*cm]
            tabla_dosis = Table(filas_dosis, colWidths=col_w)
            tabla_dosis.setStyle(TableStyle([
                ("BACKGROUND",  (0, 0), (-1, 0),  FONDO),
                ("FONTNAME",    (0, 0), (-1, 0),  "Helvetica-Bold"),
                ("FONTSIZE",    (0, 0), (-1, -1), 8),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F9FAFB")]),
                ("GRID",        (0, 0), (-1, -1), 0.25, colors.HexColor("#E5E7EB")),
                ("VALIGN",      (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING",  (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING",(0,0), (-1, -1), 4),
            ]))
            story.append(tabla_dosis)
        else:
            story.append(Paragraph("Sin dosis aplicadas aún.", sty_vacuna_sub))
 
        story.append(Spacer(1, 10))
 
    # ── Estado general ────────────────────────────────────────────────────────
    story.append(HRFlowable(width=W, thickness=1, color=AZUL, spaceBefore=4, spaceAfter=10))
    if general_completo:
        story.append(Paragraph("Esquema de vacunación general completo", sty_completo))
    else:
        story.append(Paragraph("Esquema de vacunación general incompleto", sty_incompleto))
 
    # ── Código de verificación ────────────────────────────────────────────────
    story.append(Spacer(1, 14))
    story.append(HRFlowable(width=W, thickness=0.5, color=FONDO, spaceAfter=8))
    story.append(Paragraph("Código de verificación", sty_seccion))
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        "Ingresá este código en la sección <b>Verificar Pataporte</b> del sistema para comprobar la autenticidad de este certificado.",
        sty_footer,
    ))
    story.append(Spacer(1, 6))
    story.append(Paragraph(hash_verificacion, sty_hash))
    story.append(Spacer(1, 10))
    story.append(Paragraph("Emitido por el sistema Pataporte", sty_footer))
 
    doc.build(story)
    return buffer.getvalue()



def _enviar_pdf_por_email(destinatario: str, nombre_mascota: str, pdf_bytes: bytes):
    try:
        msg = MIMEMultipart()
        msg["From"]    = settings.MAIL_FROM
        msg["To"]      = destinatario
        msg["Subject"] = f"Pataporte de vacunación — {nombre_mascota}"
 
        cuerpo_html = f"""
        <div style="font-family:Arial,sans-serif;max-width:520px;margin:auto;color:#111827;">
          <h2 style="color:#2563EB;">Pataporte</h2>
          <p>Hola,</p>
          <p>
            Adjunto encontrarás el certificado digital de vacunación de
            <strong>{nombre_mascota}</strong>, generado desde el sistema Pataporte.
          </p>
          <p>
            El PDF contiene un <strong>código de verificación</strong> que podés
            ingresar en la sección <em>Verificar Pataporte</em> del sistema para
            confirmar su autenticidad en cualquier momento.
          </p>
          <hr style="border:none;border-top:1px solid #E5E7EB;margin:20px 0;" />
          <p style="font-size:12px;color:#6B7280;">
            Este correo fue enviado automáticamente por el sistema Pataporte.
          </p>
        </div>
        """
 
        msg.attach(MIMEText(cuerpo_html, "html"))
 
        adjunto = MIMEBase("application", "pdf")
        adjunto.set_payload(pdf_bytes)
        encoders.encode_base64(adjunto)
        adjunto.add_header(
            "Content-Disposition",
            f'attachment; filename="pataporte_{nombre_mascota.lower().replace(" ", "_")}.pdf"',
        )
        msg.attach(adjunto)
 
        enviar_email(destinatario, msg)
 
    except Exception as e:
        raise RuntimeError("No se pudo enviar el PDF") from e