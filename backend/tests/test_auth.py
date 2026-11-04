import jwt
import pytest
from fastapi import HTTPException

from config.settings import settings
from utils import auth


def token(**claims):
    return jwt.encode(claims, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def detalle_401(fn, tok):
    with pytest.raises(HTTPException) as e:
        fn(tok)
    assert e.value.status_code == 401
    return e.value.detail


def test_vet_exige_rol_veterinario():
    assert auth.get_current_vet(token(sub="v1", rol="veterinario")) == "v1"
    assert detalle_401(auth.get_current_vet, token(sub="t1", rol="tutor")) == "No autorizado"
    assert detalle_401(auth.get_current_vet, token(rol="veterinario")) == "Token inválido"
    assert detalle_401(auth.get_current_vet, "basura") == "No autorizado"


def test_user_acepta_ambos_roles():
    assert auth.get_current_user(token(sub="t1", rol="tutor")) == {"id": "t1", "rol": "tutor"}
    assert detalle_401(auth.get_current_user, token(sub="x", rol="admin")) == "Token inválido"


def test_tutor_solo_exige_sub():
    assert auth.get_current_tutor(token(sub="v1", rol="veterinario")) == "v1"
    assert detalle_401(auth.get_current_tutor, token(rol="tutor")) == "Token inválido"
