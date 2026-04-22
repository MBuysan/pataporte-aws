import uuid
from datetime import datetime, date

from sqlalchemy import (
    create_engine, text,
    String, VARCHAR, Text, Boolean, SmallInteger, Date, DateTime,
    ForeignKey, UniqueConstraint, CheckConstraint, Index,
    Enum as SAEnum,
)
from sqlalchemy.orm import sessionmaker, DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from config.settings import settings

# ── Motor y sesion ────────────────────────────────────────────────────────────
engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Base(DeclarativeBase):
    pass

# ── ENUMs (reflejan los tipos del DDL) ───────────────────────────────────────
estado_general_enum = SAEnum("activo", "inactivo",                                    name="estado_general")
estado_esquema_enum = SAEnum("activo", "completado", "atrasado",                      name="estado_esquema")
estado_cert_enum    = SAEnum("vigente", "pendiente_revision", "vencido", "revocado",  name="estado_cert")
sexo_mascota_enum   = SAEnum("macho", "hembra", "desconocido",                        name="sexo_mascota")
rol_tutor_enum      = SAEnum("principal", "secundario",                               name="rol_tutor")

# ── MODELOS ───────────────────────────────────────────────────────────────────
class UsuarioTutor(Base):
    __tablename__ = "usuario_tutor"
    
    id_tutor:       Mapped[str]      = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    cedula:         Mapped[str]      = mapped_column(VARCHAR(20),  nullable=False, unique=True)
    nombre:         Mapped[str]      = mapped_column(VARCHAR(120), nullable=False)
    email:          Mapped[str]      = mapped_column(VARCHAR(254), nullable=False, unique=True)
    telefono:       Mapped[str|None] = mapped_column(VARCHAR(30),  nullable=True)
    password_hash:  Mapped[str]      = mapped_column(VARCHAR(255), nullable=False)
    fecha_registro: Mapped[datetime] = mapped_column(DateTime,     nullable=False, default=datetime.utcnow)
    estado:         Mapped[str]      = mapped_column(estado_general_enum, nullable=False, default="activo")

    mascotas: Mapped[list["MascotaTutor"]] = relationship("MascotaTutor", back_populates="tutor")


class Mascota(Base):
    __tablename__ = "mascota"

    id_mascota:          Mapped[str]       = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    nombre:              Mapped[str]       = mapped_column(VARCHAR(100), nullable=False)
    fecha_de_nacimiento: Mapped[date|None] = mapped_column(Date, nullable=True)
    sexo:                Mapped[str]       = mapped_column(sexo_mascota_enum, nullable=False, default="desconocido")
    especie:             Mapped[str]       = mapped_column(VARCHAR(60), nullable=False)
    raza:                Mapped[str|None]  = mapped_column(VARCHAR(60), nullable=True)
    foto_url:            Mapped[str|None]  = mapped_column(Text, nullable=True)
    fecha_registro:      Mapped[datetime]  = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    estado:              Mapped[str]       = mapped_column(estado_general_enum, nullable=False, default="activo")

    tutores:      Mapped[list["MascotaTutor"]]     = relationship("MascotaTutor",     back_populates="mascota")
    consultas:    Mapped[list["Consulta"]]          = relationship("Consulta",          back_populates="mascota")
    tratamientos: Mapped[list["Tratamiento"]]       = relationship("Tratamiento",       back_populates="mascota")
    esquemas:     Mapped[list["EsquemaVacunacion"]] = relationship("EsquemaVacunacion", back_populates="mascota")


class MascotaTutor(Base):
    #Tabla intermedia N:M. Solo puede haber un tutor principal por mascota (índice parcial).
    __tablename__ = "mascota_tutor"
    
    id_tutor:         Mapped[str]      = mapped_column(UUID(as_uuid=False), ForeignKey("usuario_tutor.id_tutor", ondelete="RESTRICT",  onupdate="CASCADE"), primary_key=True)
    id_mascota:       Mapped[str]      = mapped_column(UUID(as_uuid=False), ForeignKey("mascota.id_mascota",     ondelete="CASCADE",   onupdate="CASCADE"), primary_key=True)
    rol_tutor:        Mapped[str]      = mapped_column(rol_tutor_enum, nullable=False, default="secundario")
    fecha_asignacion: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    tutor:   Mapped["UsuarioTutor"] = relationship("UsuarioTutor", back_populates="mascotas")
    mascota: Mapped["Mascota"]      = relationship("Mascota",      back_populates="tutores")


class CodigoAccesoMascota(Base):
    __tablename__ = "codigo_acceso_mascota"

    id_codigo:        Mapped[str]      = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    id_mascota:       Mapped[str]      = mapped_column(UUID(as_uuid=False), ForeignKey("mascota.id_mascota", ondelete="CASCADE", onupdate="CASCADE"), nullable=False)
    codigo:           Mapped[str]      = mapped_column(VARCHAR(20), nullable=False, unique=True)
    fecha_creacion:   Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    fecha_expiracion: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    usado:            Mapped[bool]     = mapped_column(Boolean, nullable=False, default=False)

    mascota: Mapped["Mascota"] = relationship("Mascota")


class Veterinaria(Base):
    __tablename__ = "veterinaria"

    id_veterinaria:        Mapped[str]      = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    cedula_veterinario:    Mapped[str]      = mapped_column(VARCHAR(20),  nullable=False, unique=True)
    matricula_profesional: Mapped[str]      = mapped_column(VARCHAR(40),  nullable=False, unique=True)
    nombre:                Mapped[str]      = mapped_column(VARCHAR(120), nullable=False)
    email:                 Mapped[str]      = mapped_column(VARCHAR(254), nullable=False, unique=True)
    password_hash:         Mapped[str]      = mapped_column(VARCHAR(255), nullable=False)
    estado:                Mapped[str]      = mapped_column(estado_general_enum, nullable=False, default="activo")
    fecha_registro:        Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    consultas:              Mapped[list["Consulta"]]    = relationship("Consulta",    back_populates="veterinario")
    dosis:                  Mapped[list["Dosis"]]       = relationship("Dosis",       back_populates="veterinario")
    certificados_emitidos:  Mapped[list["Certificado"]] = relationship("Certificado", back_populates="emisor",  foreign_keys="Certificado.id_veterinario_emisor")
    certificados_revisados: Mapped[list["Certificado"]] = relationship("Certificado", back_populates="revisor", foreign_keys="Certificado.id_revisor")


class Consulta(Base):
    __tablename__ = "consulta"
    __table_args__ = (
        #Constraint: si editado=TRUE, fecha_edicion no puede ser NULL y viceversa
        CheckConstraint(
            "(editado = FALSE AND fecha_edicion IS NULL) OR (editado = TRUE AND fecha_edicion IS NOT NULL)",
            name="chk_edicion"
        ),
    )

    id_consulta:          Mapped[str]           = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    id_mascota:           Mapped[str]           = mapped_column(UUID(as_uuid=False), ForeignKey("mascota.id_mascota",        ondelete="RESTRICT", onupdate="CASCADE"), nullable=False)
    id_veterinario:       Mapped[str]           = mapped_column(UUID(as_uuid=False), ForeignKey("veterinaria.id_veterinaria", ondelete="RESTRICT", onupdate="CASCADE"), nullable=False)
    fecha_hora:           Mapped[datetime]      = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    motivo:               Mapped[str]           = mapped_column(Text, nullable=False)
    diagnostico:          Mapped[str|None]      = mapped_column(Text, nullable=True)
    tratamiento_indicado: Mapped[str|None]      = mapped_column(Text, nullable=True)
    editado:              Mapped[bool]          = mapped_column(Boolean, nullable=False, default=False)
    fecha_edicion:        Mapped[datetime|None] = mapped_column(DateTime, nullable=True)

    mascota:     Mapped["Mascota"]     = relationship("Mascota",     back_populates="consultas")
    veterinario: Mapped["Veterinaria"] = relationship("Veterinaria", back_populates="consultas")


class Tratamiento(Base):
    __tablename__ = "tratamiento"
    __table_args__ = (
        UniqueConstraint("id_mascota", "nombre", name="uq_trat_nombre_mascota"),
        CheckConstraint(
            "fecha_fin_real IS NULL OR fecha_fin_real >= fecha_inicio",
            name="chk_trat_fechas",
        ),
    )

    id_tratamiento: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )

    id_mascota: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("mascota.id_mascota", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=False
    )

    id_consulta: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("consulta.id_consulta", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=False
    )

    nombre: Mapped[str] = mapped_column(VARCHAR(150), nullable=False)
    indicaciones: Mapped[str] = mapped_column(Text, nullable=False)
    fecha_inicio: Mapped[date] = mapped_column(Date, nullable=False)
    fecha_fin_estimada: Mapped[date] = mapped_column(Date, nullable=False)
    fecha_fin_real: Mapped[date | None] = mapped_column(Date, nullable=True)

    mascota: Mapped["Mascota"] = relationship("Mascota", back_populates="tratamientos")
    consulta: Mapped["Consulta"] = relationship("Consulta")


class TipoVacunas(Base):
    __tablename__ = "tipo_vacunas"

    id_vacuna:                  Mapped[str]      = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    nombre:                     Mapped[str]      = mapped_column(VARCHAR(120), nullable=False, unique=True)
    descripcion:                Mapped[str|None] = mapped_column(Text, nullable=True)
    especie_objetivo:           Mapped[str|None] = mapped_column(VARCHAR(60), nullable=True)
    cantidad_dosis_requeridas:  Mapped[int]      = mapped_column(SmallInteger, nullable=False)
    intervalo_entre_dosis_dias: Mapped[int|None] = mapped_column(SmallInteger, nullable=True)
    intervalo_refuerzo_dias:    Mapped[int|None] = mapped_column(SmallInteger, nullable=True)
    activo:                     Mapped[bool]     = mapped_column(Boolean, nullable=False, default=True)

    esquemas: Mapped[list["EsquemaVacunacion"]] = relationship("EsquemaVacunacion", back_populates="tipo_vacuna")


class EsquemaVacunacion(Base):
    __tablename__ = "esquema_vacunacion"
    __table_args__ = (
        #Una mascota no puede tener dos esquemas activos del mismo tipo de vacuna
        UniqueConstraint("id_mascota", "id_vacuna", "estado", name="uq_esquema_activo"),
    )

    id_esquema:          Mapped[str]       = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    id_mascota:          Mapped[str]       = mapped_column(UUID(as_uuid=False), ForeignKey("mascota.id_mascota",     ondelete="RESTRICT", onupdate="CASCADE"), nullable=False)
    id_vacuna:           Mapped[str]       = mapped_column(UUID(as_uuid=False), ForeignKey("tipo_vacunas.id_vacuna", ondelete="RESTRICT", onupdate="CASCADE"), nullable=False)
    fecha_inicio:        Mapped[date]      = mapped_column(Date, nullable=False, default=date.today)
    estado:              Mapped[str]       = mapped_column(estado_esquema_enum, nullable=False, default="activo")
    fecha_proxima_dosis: Mapped[date|None] = mapped_column(Date, nullable=True)

    mascota:     Mapped["Mascota"]      = relationship("Mascota",      back_populates="esquemas")
    tipo_vacuna: Mapped["TipoVacunas"]  = relationship("TipoVacunas",  back_populates="esquemas")
    dosis:       Mapped[list["Dosis"]]  = relationship("Dosis",        back_populates="esquema")


class Dosis(Base):
    __tablename__ = "dosis"
    __table_args__ = (
        UniqueConstraint("id_esquema", "numero_dosis", name="uq_dosis_numero_esquema"),
    )

    id_dosis:           Mapped[str]       = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    id_esquema:         Mapped[str]       = mapped_column(UUID(as_uuid=False), ForeignKey("esquema_vacunacion.id_esquema", ondelete="RESTRICT", onupdate="CASCADE"), nullable=False)
    id_veterinaria:     Mapped[str]       = mapped_column(UUID(as_uuid=False), ForeignKey("veterinaria.id_veterinaria",   ondelete="RESTRICT", onupdate="CASCADE"), nullable=False)
    numero_dosis:       Mapped[int]       = mapped_column(SmallInteger, nullable=False)
    fecha_aplicacion:   Mapped[date]      = mapped_column(Date, nullable=False, default=date.today)
    fecha_programada:   Mapped[date|None] = mapped_column(Date, nullable=True)
    lote_vacuna:        Mapped[str|None]  = mapped_column(VARCHAR(60), nullable=True)
    via_administracion: Mapped[str|None]  = mapped_column(VARCHAR(60), nullable=True)
    observaciones:      Mapped[str|None]  = mapped_column(Text, nullable=True)
    es_externa:         Mapped[bool]      = mapped_column(Boolean, nullable=False, default=False)

    esquema:     Mapped["EsquemaVacunacion"] = relationship("EsquemaVacunacion", back_populates="dosis")
    veterinario: Mapped["Veterinaria"]       = relationship("Veterinaria",       back_populates="dosis")
    certificado: Mapped["Certificado|None"]  = relationship("Certificado",       back_populates="dosis", uselist=False)


class Certificado(Base):
    __tablename__ = "certificado"
    __table_args__ = (
        UniqueConstraint("id_dosis",             name="uq_cert_dosis"),
        UniqueConstraint("hash_verificacion",    name="uq_cert_hash"),
        # Si es certificacion manual y esta vigente, debe tener revisor
        CheckConstraint(
            "certificacion_manual = FALSE OR estado != 'vigente' OR id_revisor IS NOT NULL",
            name="chk_cert_manual"
        ),
    )

    id_certificado:         Mapped[str]       = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    id_dosis:               Mapped[str]       = mapped_column(UUID(as_uuid=False), ForeignKey("dosis.id_dosis",              ondelete="RESTRICT",  onupdate="CASCADE"), nullable=False)
    id_veterinario_emisor:  Mapped[str]       = mapped_column(UUID(as_uuid=False), ForeignKey("veterinaria.id_veterinaria",  ondelete="RESTRICT",  onupdate="CASCADE"), nullable=False)
    id_revisor:             Mapped[str|None]  = mapped_column(UUID(as_uuid=False), ForeignKey("veterinaria.id_veterinaria",  ondelete="SET NULL",  onupdate="CASCADE"), nullable=True)
    hash_verificacion:      Mapped[str|None]  = mapped_column(VARCHAR(128), nullable=True)
    url_documento:          Mapped[str|None]  = mapped_column(Text, nullable=True)
    estado:                 Mapped[str]       = mapped_column(estado_cert_enum, nullable=False, default="pendiente_revision")
    fecha_emision:          Mapped[datetime]  = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    fecha_vencimiento:      Mapped[date|None] = mapped_column(Date, nullable=True)
    certificacion_manual:   Mapped[bool]      = mapped_column(Boolean, nullable=False, default=False)
    observaciones_revision: Mapped[str|None]  = mapped_column(Text, nullable=True)

    dosis:   Mapped["Dosis"]            = relationship("Dosis",       back_populates="certificado")
    emisor:  Mapped["Veterinaria"]      = relationship("Veterinaria", back_populates="certificados_emitidos",  foreign_keys=[id_veterinario_emisor])
    revisor: Mapped["Veterinaria|None"] = relationship("Veterinaria", back_populates="certificados_revisados", foreign_keys=[id_revisor])

class RecuperacionPassword(Base):
     """
     Guarda los codigos de recuperacion de contraseña.
     - El codigo se genera al solicitar recuperacion y expira en 15 minutos.
     - Una vez usado, la columna 'usado' se marca True y no puede reutilizarse.
     - Relacion con UsuarioTutor via id_tutor (ForeignKey).
     """
     __tablename__ = "recuperacion_password"

     id_recuperacion: Mapped[str]      = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
     id_tutor:        Mapped[str]      = mapped_column(UUID(as_uuid=False), ForeignKey("usuario_tutor.id_tutor", ondelete="CASCADE", onupdate="CASCADE"), nullable=False)
     codigo_hash:     Mapped[str]      = mapped_column(VARCHAR(255), nullable=False)
     expiracion:      Mapped[datetime] = mapped_column(DateTime, nullable=False)
     usado:           Mapped[bool]     = mapped_column(Boolean, nullable=False, default=False)
     fecha_solicitud: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

     tutor: Mapped["UsuarioTutor"] = relationship("UsuarioTutor")
 
# ── Sesion y utilidades ───────────────────────────────────────────────────────

def get_db():
    """
    Dependencia de FastAPI: provee una sesion de BD por request y la cierra al terminar.
    Uso en routers:
        def mi_endpoint(db: Session = Depends(get_db)):
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    """
    Crea todas las tablas en la BD si no existen.
    Solo para desarrollo rapido. En produccion usar: alembic upgrade head
    """
    Base.metadata.create_all(bind=engine)