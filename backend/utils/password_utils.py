import re

def validar_password(password: str) -> None:
    """
    Valida la contraseña según reglas de seguridad.
    Lanza ValueError si algo no cumple.
    """

    if not password:
        raise ValueError("La contraseña no puede estar vacía")

    if len(password) < 6:
        raise ValueError("La contraseña debe tener al menos 6 caracteres")

    if not re.search(r"[A-Z]", password):
        raise ValueError("Debe tener al menos una mayúscula")

    if not re.search(r"[a-z]", password):
        raise ValueError("Debe tener al menos una minúscula")

    if not re.search(r"\d", password):
        raise ValueError("Debe tener al menos un número")

    if not re.search(r"[!@#$%^&*(),.?\":{}|<>_\-]", password):
        raise ValueError("Debe tener al menos un carácter especial")