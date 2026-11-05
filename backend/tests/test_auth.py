import jwt
import pytest
from fastapi import HTTPException

from config.settings import settings
from utils import auth


def token(**claims):
    return jwt.encode(claims, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def detalle(fn, tok, status=401):
    with pytest.raises(HTTPException) as e:
        fn(tok)
    assert e.value.status_code == status
    return e.value.detail


def test_vet_exige_rol_veterinario():
    assert auth.get_current_vet(token(sub="v1", rol="veterinario")) == "v1"
    assert detalle(auth.get_current_vet, token(sub="t1", rol="tutor"), 403) == "Permisos insuficientes"
    assert detalle(auth.get_current_vet, token(rol="veterinario")) == "Token inválido"
    assert detalle(auth.get_current_vet, "basura") == "No autorizado"


def test_user_acepta_ambos_roles():
    assert auth.get_current_user(token(sub="t1", rol="tutor")) == {"id": "t1", "rol": "tutor"}
    assert detalle(auth.get_current_user, token(sub="x", rol="admin")) == "Token inválido"


def test_tutor_exige_rol_tutor():
    assert auth.get_current_tutor(token(sub="t1", rol="tutor")) == "t1"
    assert detalle(auth.get_current_tutor, token(sub="v1", rol="veterinario"), 403) == "Permisos insuficientes"
    assert detalle(auth.get_current_tutor, token(rol="tutor")) == "Token inválido"
    assert detalle(auth.get_current_tutor, "basura") == "No autorizado"
