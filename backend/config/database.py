"""Conexión de la aplicación y exportaciones compatibles de sus modelos."""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from config.settings import settings
from config.models import (
    Base,
    UsuarioTutor,
    Mascota,
    MascotaTutor,
    CodigoAccesoMascota,
    Organizacion,
    Veterinario,
    Consulta,
    Tratamiento,
    TipoVacunas,
    EsquemaVacunacion,
    EsquemaVacuna,
    Dosis,
    Pataporte,
    RecuperacionPassword,
    VerificacionEmail,
)

engine = create_engine(
    settings.sqlalchemy_url(), pool_pre_ping=True,
    connect_args=settings.database_connect_args(),
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
