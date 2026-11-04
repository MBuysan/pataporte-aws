"""Plantillas y PDFs sin conexión a PostgreSQL; reutilizables desde Lambda."""
import io
from html import escape
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
from config.mail import get_mail_settings
from utils.email import enviar_email

EXPIRACION_MINUTOS = 15


def _enviar_email_recuperacion(email: str, codigo: str):
    """
    envía código de recuperacion al email del usuario

    implementacion con smtp , es el protocolo estandar para enviar emails entre servidores

    smtplib.SMTP_SSL abre una conexión cifrada al servidor de gmail en el puerto 465.

    gmail requiere una "contraseña de aplicación" (no la contraseña de la cuenta).
      se genera en: google account → seguridad → verificación en dos pasos → contraseñas de app.


    estas variables se configuran en el .env:
        MAIL_USERNAME=tucuenta@gmail.com
        MAIL_PASSWORD=xxxx-xxxx-xxxx-xxxx
        MAIL_FROM=tucuenta@gmail.com

    """
    # MIMEMultipart("alternative") crea un email con múltiples versiones del cuerpo.
    # "alternative" significa que son versiones alternativas del mismo contenido
    # (texto plano O html) — el cliente de email elige cuál mostrar dependiendo de sus capacidades.
    settings = get_mail_settings()
    mensaje = MIMEMultipart("alternative")
    mensaje["Subject"] = "Recuperación de contraseña - Pataporte"
    mensaje["From"] = settings.MAIL_FROM
    mensaje["To"] = email

    # versión texto plano: para clientes que no renderizan HTML
    cuerpo_texto = f"""
Hola,

Recibimos una solicitud para recuperar tu contraseña en Pataporte.

Tu código de recuperación es: {codigo}

Este código es válido por {EXPIRACION_MINUTOS} minutos.
Si no solicitaste este cambio, podés ignorar este email.

Equipo Pataporte
    """

    # versión HTML: para clientes modernos
    cuerpo_html = f"""
    <html>
      <body style="font-family: Arial, sans-serif; color: #333;">
        <h2>Recuperación de contraseña</h2>
        <p>Recibimos una solicitud para recuperar tu contraseña en <strong>Pataporte</strong>.</p>
        <p>Tu código de recuperación es:</p>
        <div style="font-size: 32px; font-weight: bold; letter-spacing: 8px;
                    background: #f4f4f4; padding: 16px; display: inline-block;
                    border-radius: 8px; margin: 12px 0;">
          {codigo}
        </div>
        <p>Este código es válido por <strong>{EXPIRACION_MINUTOS} minutos</strong>.</p>
        <p style="color: #888; font-size: 13px;">
          Si no solicitaste este cambio, podés ignorar este email.
        </p>
      </body>
    </html>
    """

    # MIMEText envuelve el texto con el tipo MIME correcto.
    # se adjuntan ambas versiones — el cliente de email elige cuál mostrar.
    mensaje.attach(MIMEText(cuerpo_texto, "plain", "utf-8"))
    mensaje.attach(MIMEText(cuerpo_html, "html", "utf-8"))

    try:
        enviar_email(email, mensaje)

    except Exception as e:
        raise RuntimeError("No se pudo enviar el correo de recuperación") from e


def _enviar_email_verificacion(email: str, codigo: str):
    """
    Envía el código de activación de 6 dígitos tras el registro del usuario.
    Utiliza la estética azul y gris característica de la aplicación.
    """
    settings = get_mail_settings()
    mensaje = MIMEMultipart("alternative")
    mensaje["Subject"] = "Verificación de cuenta - Pataporte"
    mensaje["From"] = settings.MAIL_FROM
    mensaje["To"] = email

    cuerpo_texto = f"""
Hola,

¡Gracias por registrarte en Pataporte!

Para activar tu cuenta y comenzar a gestionar tus mascotas, utilizá el siguiente código:

Código de verificación: {codigo}

Este código expira en {EXPIRACION_MINUTOS} minutos.

Equipo Pataporte
    """

    cuerpo_html = f"""
    <html>
      <body style="font-family: Arial, sans-serif; color: #333; background-color: #f9f9f9; padding: 20px; margin: 0;">
        <div style="max-width: 500px; background: #ffffff; border-radius: 12px; padding: 30px; margin: 0 auto;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.05); border: 1px solid #eee;">
          <h2 style="color: #222; font-size: 22px; margin-top: 0;">Verificación de cuenta</h2>
          <p style="font-size: 15px; line-height: 1.5; color: #555;">
            ¡Gracias por registrarte en <strong>Pataporte</strong>! Para activar tu cuenta y acceder al sistema, ingresá el siguiente código:
          </p>
          <div style="text-align: center; margin: 24px 0;">
            <div style="font-size: 32px; font-weight: bold; letter-spacing: 8px;
                        background: #dde8f8; color: #4a90e2; padding: 16px 24px; display: inline-block;
                        border-radius: 8px; border: 1px dashed #4a90e2;">
              {codigo}
            </div>
          </div>
          <p style="font-size: 14px; color: #888;">
            Este código es válido por <strong>{EXPIRACION_MINUTOS} minutos</strong>.
          </p>
          <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;" />
          <p style="color: #aaa; font-size: 12px; text-align: center; margin-bottom: 0;">
            Si no realizaste este registro en nuestro sitio, podés descartar este email tranquilamente.
          </p>
        </div>
      </body>
    </html>
    """

    mensaje.attach(MIMEText(cuerpo_texto, "plain", "utf-8"))
    mensaje.attach(MIMEText(cuerpo_html, "html", "utf-8"))

    try:
        enviar_email(email, mensaje)

    except Exception as e:
        raise RuntimeError("No se pudo enviar el correo de verificación") from e


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
    fecha_emision = escape(str(credencial.get("issuanceDate", ""))[:10])
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
        return [Paragraph(label, sty_campo_lbl), Paragraph(escape(str(value)) if value else "—", sty_campo_val)]

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
            [[Paragraph(escape(str(vac["nombre"])), sty_vacuna_nom), Paragraph(badge, badge_sty)]],
            colWidths=[W * 0.55, W * 0.45],
        )
        encabezado_vac.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN",  (1, 0), (1, 0),   "RIGHT"),
        ]))
        story.append(encabezado_vac)

        if vac.get("descripcion"):
            story.append(Paragraph(escape(str(vac["descripcion"])), sty_vacuna_sub))

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
                    Paragraph(escape(f"#{d['numero']}"), sty_dosis_row),
                    Paragraph(escape(str(d.get("fecha", "—"))), sty_dosis_row),
                    Paragraph(escape(str(vet_ap.get("nombre") or "—")), sty_dosis_row),
                    Paragraph(escape(str(vet_ap.get("matricula") or "—")), sty_dosis_row),
                    Paragraph(escape(str(vet_ap.get("organizacion_rut") or "—")), sty_dosis_row),
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
    story.append(Paragraph(escape(str(hash_verificacion)), sty_hash))
    story.append(Spacer(1, 10))
    story.append(Paragraph("Emitido por el sistema Pataporte", sty_footer))

    doc.build(story)
    return buffer.getvalue()


def _enviar_pdf_por_email(destinatario: str, nombre_mascota: str, pdf_bytes: bytes):
    try:
        settings = get_mail_settings()
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
            <strong>{escape(nombre_mascota)}</strong>, generado desde el sistema Pataporte.
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
