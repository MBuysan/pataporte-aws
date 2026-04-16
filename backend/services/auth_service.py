import random
import string
from datetime import datetime, timedelta

from fastapi import HTTPException
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from config.database import UsuarioTutor, RecuperacionPassword
from backend.schemas.recuperacion_password import SolicitarRecuperacionRequest, ResetPasswordRequest

# configuracion de hashing
# CryptContext es el objeto que sabe como hashear y verificar con bcrypt.
# "deprecated=auto" significa que si en el futuro cambiamos el algoritmo, los hashes viejos se reconocen igual y se migran solitos.
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

EXPIRACION_MINUTOS = 15


#  funciones privadas (con _ al inicio = uso interno del modulo)

def _generar_codigo() -> str:
    """
    genera un codigo alfanumerico de 6 caracteres en mayusculas. Ejemplo: 'A3F7KP'
    random.choices elige caracteres al azar de la lista dada, con repeticion permitida.
    """
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=6))


def _hashear(texto: str) -> str:
    """transforma texto plano en hash bcrypt."""
    return pwd_context.hash(texto)


def _verificar(texto_plano: str, hash_guardado: str) -> bool:
    """
    compara texto plano contra su hash. devuelve true si coinciden.
    """
    return pwd_context.verify(texto_plano, hash_guardado)


def _enviar_email_recuperacion(email: str, codigo: str):
    """
    falta implementar envio real con SendGrid, SMTP, etc.
    por ahora imprime en consola para probarlo en desarrollo.
    """
    print(f"[RECUPERACION] Email: {email} | Codigo: {codigo} | Expira en {EXPIRACION_MINUTOS} min")


#  funciones publicas (las llaman los routers) 

def solicitar_recuperacion(db: Session, data: SolicitarRecuperacionRequest):
    """
    Paso 1: el usuario ingresa su email.

    Logica de seguridad importante:
    - Si el email NO existe, la respuesta es IDENTICA a si existe.
    - Esto evita que alguien pueda usar este endpoint para descubrir
      que emails estan registrados en el sistema (ataque de enumeracion).
    """
    # db.query(Modelo).filter(condicion).first() → busca el primer registro que cumpla la condicion, o None si no existe
    tutor = db.query(UsuarioTutor).filter(UsuarioTutor.email == data.email).first()

    if not tutor:
        # misma respuesta aunque no exista (por seguridad)
        return {"mensaje": "Si el email está registrado, recibirás un código de recuperación"}

    # invalida codigos anteriores pendientes del mismo tutor.
    # .update({}) modifica todos los registros que matcheen el filter de una sola vez.
    db.query(RecuperacionPassword).filter(
        RecuperacionPassword.id_tutor == tutor.id_tutor,
        RecuperacionPassword.usado    == False
    ).update({"usado": True})

    # genera el codigo, lo hashea y calcula su fecha de expiracion
    codigo_plano = _generar_codigo()
    codigo_hash  = _hashear(codigo_plano)
    expiracion   = datetime.utcnow() + timedelta(minutes=EXPIRACION_MINUTOS)

    # crea el objeto python del modelo 
    recuperacion = RecuperacionPassword(
        id_tutor    = tutor.id_tutor,
        codigo_hash = codigo_hash,
        expiracion  = expiracion,
        usado       = False,
    )

    # db.add() → lo encola para insertar
    # db.commit() → ejecuta el INSERT en la BD
    db.add(recuperacion)
    db.commit()

    _enviar_email_recuperacion(tutor.email, codigo_plano)

    return {"mensaje": "Si el email está registrado, recibirás un código de recuperación"}


def resetear_password(db: Session, data: ResetPasswordRequest):
    """
    Paso 2: el usuario ingresa el codigo recibido y su nueva contraseña.

    Validaciones en orden:
    1. El codigo existe, no fue usado y no expiro.
    2. La nueva contraseña es distinta a la anterior.
    3. Actualiza password_hash y marca el codigo como usado.

    Nota: las validaciones de FORMATO de contraseña (mayuscula, numero, etc.)
    ya las hizo Pydantic en el schema antes de llegar aqui.
    """

    # Busca todos los codigos que tecnicamente podrian ser validos
    # (no usados y no expirados). Luego verifica cual matchea con bcrypt.
    # No podemos hacer WHERE codigo_hash = ? porque bcrypt genera hashes
    # distintos cada vez aunque el texto sea el mismo.
    recuperaciones_candidatas = db.query(RecuperacionPassword).filter(
        RecuperacionPassword.usado      == False,
        RecuperacionPassword.expiracion >  datetime.utcnow()
    ).all()

    # recorre los candidatos hasta encontrar uno cuyo hash coincida con el codigo ingresado
    recuperacion = None
    for r in recuperaciones_candidatas:
        if _verificar(data.codigo, r.codigo_hash):
            recuperacion = r
            break  # encontrado, no necesitamos seguir buscando

    if not recuperacion:
        raise HTTPException(
            status_code=400,
            detail="El código es inválido o ha expirado"
        )

    # Obtiene el tutor dueno de ese codigo
    tutor = db.query(UsuarioTutor).filter(
        UsuarioTutor.id_tutor == recuperacion.id_tutor
    ).first()

    if not tutor:
        raise HTTPException(status_code=404, detail="Tutor no encontrado")

    # verifica que la nueva contraseña sea diferente a la actual.
    # _verificar compara texto plano contra el hash guardado en la BD.
    if _verificar(data.nueva_password, tutor.password_hash):
        raise HTTPException(
            status_code=400,
            detail="La nueva contraseña no puede ser igual a la anterior"
        )

    # actualiza el campo password_hash en el objeto tutor
    # (SQLAlchemy detecta el cambio y lo incluye en el proximo commit)
    tutor.password_hash = _hashear(data.nueva_password)

    # Marca el codigo como usado para que no pueda reutilizarse
    recuperacion.usado = True

    # db.commit() guarda AMBOS cambios en la BD en una sola transaccion
    db.commit()

    return {"mensaje": "Contraseña actualizada correctamente"}