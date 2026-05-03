import random
import string
import smtplib
import traceback
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from fastapi import HTTPException
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from config.database import UsuarioTutor, RecuperacionPassword, Veterinaria
from schemas.recuperacion_password import (
    SolicitarRecuperacionRequest,
    ResetPasswordRequest,
)
from datetime import datetime, timedelta, timezone
import jwt
from sqlalchemy import or_
from config.settings import settings

"""
configuracion de hashing 
    CryptContext es el objeto que sabe como hashear y verificar con bcrypt.
    "deprecated=auto" significa que si en el futuro cambiamos el algoritmo,
    los hashes viejos se reconocen igual y se migran solitos.
"""

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

EXPIRACION_MINUTOS = 15


# funciones privadas (con _ al inicio = uso interno del modulo)


def _generar_codigo() -> str:
    """
    genera un codigo alfanumerico de 6 caracteres en mayusculas. Ejemplo: 'A3F7KP'
    random.choices elige caracteres al azar de la lista dada, con repeticion permitida.
    """
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=6))


def _hashear(texto: str) -> str:
    """transforma texto plano en hash bcrypt."""
    return pwd_context.hash(texto)


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
        # SMTP_SSL abre una conexión cifrada directamente en el puerto 465.
        # "with" garantiza que la conexión se cierre aunque ocurra un error.
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as servidor:
            servidor.login(settings.MAIL_USERNAME, settings.MAIL_PASSWORD)
            # sendmail(remitente, [destinatarios], mensaje_serializado_como_texto)
            servidor.sendmail(settings.MAIL_FROM, email, mensaje.as_string())

    except Exception as e:
        # si el email falla, se registra pero no se interrumpe el flujo.
        # el código ya fue guardado en la BD — el usuario puede pedir otro.
        traceback.print_exc()
        print(f"[ERROR EMAIL] No se pudo enviar email a {email}: {e}")


#  funciones publicas (las llaman los routers)


def solicitar_recuperacion(db: Session, data: SolicitarRecuperacionRequest):
    """
    Paso 1: el usuario ingresa su email.

    Logica de seguridad importante:
    - Si el email NO existe, la respuesta es IDENTICA a si existe.
    - Esto evita que alguien pueda usar este endpoint para descubrir
      que emails estan registrados en el sistema.
    """
    # db.query(Modelo).filter(condicion).first() → busca el primer registro que cumpla la condicion, o None si no existe
    tutor = db.query(UsuarioTutor).filter(UsuarioTutor.email == data.email).first()

    if not tutor:
        return {
            "mensaje": "Si el email está registrado, recibirás un código de recuperación"
        }

    # invalida codigos anteriores pendientes del mismo tutor.
    # .update({}) modifica todos los registros que matcheen el filter de una sola vez.
    db.query(RecuperacionPassword).filter(
        RecuperacionPassword.id_tutor == tutor.id_tutor,
        RecuperacionPassword.usado == False,
    ).update({"usado": True})

    # genera el codigo, lo hashea y calcula su fecha de expiracion
    codigo_plano = _generar_codigo()
    codigo_hash = _hashear(codigo_plano)
    expiracion = datetime.utcnow() + timedelta(minutes=EXPIRACION_MINUTOS)

    # crea el objeto python del modelo
    recuperacion = RecuperacionPassword(
        id_tutor=tutor.id_tutor,
        codigo_hash=codigo_hash,
        expiracion=expiracion,
        usado=False,
    )

    # db.add() → lo encola para insertar
    # db.commit() → ejecuta el INSERT en la BD
    db.add(recuperacion)
    db.commit()

    _enviar_email_recuperacion(tutor.email, codigo_plano)

    return {
        "mensaje": "Si el email está registrado, recibirás un código de recuperación"
    }


def resetear_password(db: Session, data: ResetPasswordRequest):
    """
    Paso 2: el usuario ingresa el codigo recibido y su nueva contraseña.

    Validaciones en orden:
    1. El codigo existe, no fue usado y no expiro.
    2. La nueva contraseña es distinta a la anterior.
    3. Actualiza password_hash y marca el codigo como usado.

    """

    # Busca todos los codigos que tecnicamente podrian ser validos
    # (no usados y no expirados). Luego verifica cual matchea con bcrypt.
    # No se puede hacer hacer WHERE codigo_hash = ? porque bcrypt genera hashes
    # distintos cada vez aunque el texto sea el mismo.
    recuperaciones_candidatas = (
        db.query(RecuperacionPassword)
        .filter(
            RecuperacionPassword.usado == False,
            RecuperacionPassword.expiracion > datetime.utcnow(),
        )
        .all()
    )

    # recorre los candidatos hasta encontrar uno cuyo hash coincida con el codigo ingresado
    recuperacion = None
    for r in recuperaciones_candidatas:
        if verificar_password(data.codigo, r.codigo_hash):
            recuperacion = r
            break  # encontrado, no necesitamos seguir buscando

    if not recuperacion:
        raise HTTPException(
            status_code=400, detail="El código es inválido o ha expirado"
        )

    # obtiene el tutor dueño de ese codigo
    tutor = (
        db.query(UsuarioTutor)
        .filter(UsuarioTutor.id_tutor == recuperacion.id_tutor)
        .first()
    )

    if not tutor:
        raise HTTPException(status_code=404, detail="Tutor no encontrado")

    # verifica que la nueva contraseña sea diferente a la actual.
    # verificar_password compara texto plano contra el hash guardado en la BD.
    if verificar_password(data.nueva_password, tutor.password_hash):
        raise HTTPException(
            status_code=400,
            detail="La nueva contraseña no puede ser igual a la anterior",
        )

    # actualiza el campo password_hash en el objeto tutor
    # (SQLAlchemy detecta el cambio y lo incluye en el proximo commit)
    tutor.password_hash = _hashear(data.nueva_password)

    # Marca el codigo como usado para que no pueda reutilizarse
    recuperacion.usado = True

    # db.commit() guarda ambos cambios en la BD en una sola transaccion
    db.commit()

    return {"mensaje": "Contraseña actualizada correctamente"}


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verificar_password(password_plano: str, password_hash: str) -> bool:
    try:
        return pwd_context.verify(password_plano, password_hash)
    except ValueError:
        return False


def crear_access_token(data: dict) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )

    payload = data.copy()
    payload.update({"exp": expire})

    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return token


def login_tutor(db: Session, identificador: str, password: str):
    tutor = (
        db.query(UsuarioTutor)
        .filter(
            UsuarioTutor.estado == "activo",
            or_(
                UsuarioTutor.email == identificador,
                UsuarioTutor.cedula == identificador,
            ),
        )
        .first()
    )

    if not tutor:
        raise HTTPException(status_code=401, detail="Credenciales inválidas")

    if not verificar_password(password, tutor.password_hash):
        raise HTTPException(status_code=401, detail="Credenciales inválidas")

    access_token = crear_access_token(
        {
            "sub": tutor.id_tutor,
            "rol": "tutor",
            "nombre": tutor.nombre,
            "email": tutor.email,
        }
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id_tutor": tutor.id_tutor,
            "nombre": tutor.nombre,
            "email": tutor.email,
            "cedula": tutor.cedula,
        },
    }

def login_veterinaria(db: Session, identificador: str, password: str):
    vet = (
        db.query(Veterinaria)
        .filter(
            Veterinaria.estado == "activo",
            or_(
                Veterinaria.email == identificador,
                Veterinaria.rut == identificador,
            ),
        )
        .first()
    )

    if not vet:
        raise HTTPException(status_code=401, detail="Credenciales inválidas")

    if not verificar_password(password, vet.password_hash):
        raise HTTPException(status_code=401, detail="Credenciales inválidas")

    access_token = crear_access_token(
        {
            "sub": vet.id_veterinaria,
            "rol": "veterinaria",
            "nombre": vet.nombre,
            "email": vet.email,
        }
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id_veterinaria": vet.id_veterinaria,
            "nombre": vet.nombre,
            "email": vet.email,
            "rut": vet.rut,
        },
    }
