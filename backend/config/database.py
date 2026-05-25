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
estado_general_enum = SAEnum("activo", "inactivo", "pendiente_verificacion",          name="estado_general")
estado_esquema_enum = SAEnum("activo", "completado",                                  name="estado_esquema")
estado_cert_enum    = SAEnum("vigente", "revocado",  name="estado_cert")
sexo_mascota_enum   = SAEnum("Macho", "Hembra", "Desconocido",                        name="sexo_mascota")
rol_tutor_enum      = SAEnum("principal", "secundario",                               name="rol_tutor")
especie_enum        = SAEnum("perro", "gato", "otro",                                       name="especie")

# ── MODELOS ───────────────────────────────────────────────────────────────────
class UsuarioTutor(Base):
    __tablename__ = "usuario_tutor"
    
    id_tutor:       Mapped[str]      = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    cedula:         Mapped[str]      = mapped_column(VARCHAR(20),  nullable=False, unique=True)
    nombre:         Mapped[str]      = mapped_column(VARCHAR(120), nullable=False)
    email:          Mapped[str]      = mapped_column(VARCHAR(254), nullable=False, unique=True)
    telefono:       Mapped[str|None] = mapped_column(VARCHAR(30),  nullable=True)
    password_hash:  Mapped[str]      = mapped_column(VARCHAR(255), nullable=False)
    fecha_registro: Mapped[datetime] = mapped_column(DateTime(timezone=True),     nullable=False, default=datetime.utcnow)
    estado:         Mapped[str]      = mapped_column(estado_general_enum, nullable=False, default="pendiente_verificacion")

    mascotas: Mapped[list["MascotaTutor"]] = relationship("MascotaTutor", back_populates="tutor")


class Mascota(Base):
    __tablename__ = "mascota"

    id_mascota:          Mapped[str]       = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    nombre:              Mapped[str]       = mapped_column(VARCHAR(100), nullable=False)
    fecha_de_nacimiento: Mapped[date|None] = mapped_column(Date, nullable=True)
    sexo:                Mapped[str]       = mapped_column(sexo_mascota_enum, nullable=False, default="desconocido")
    especie:             Mapped[str]       = mapped_column(especie_enum, nullable=False)
    raza:                Mapped[str|None]  = mapped_column(VARCHAR(60), nullable=True)
    foto_url:            Mapped[str|None]  = mapped_column(Text, nullable=True)
    fecha_registro:      Mapped[datetime]  = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    estado:              Mapped[str]       = mapped_column(estado_general_enum, nullable=False, default="activo")

    tutores:      Mapped[list["MascotaTutor"]]      = relationship("MascotaTutor",      back_populates="mascota",cascade="all, delete-orphan",)    
    consultas:    Mapped[list["Consulta"]]          = relationship("Consulta",          back_populates="mascota",cascade="all, delete-orphan",)
    tratamientos: Mapped[list["Tratamiento"]]       = relationship("Tratamiento",       back_populates="mascota",cascade="all, delete-orphan",)
    esquemas:     Mapped[list["EsquemaVacunacion"]] = relationship("EsquemaVacunacion", back_populates="mascota",cascade="all, delete-orphan",)


class MascotaTutor(Base):
    #Tabla intermedia N:M. Solo puede haber un tutor principal por mascota (índice parcial).
    __tablename__ = "mascota_tutor"
    
    id_tutor:         Mapped[str]      = mapped_column(UUID(as_uuid=False), ForeignKey("usuario_tutor.id_tutor", ondelete="RESTRICT",  onupdate="CASCADE"), primary_key=True)
    id_mascota:       Mapped[str]      = mapped_column(UUID(as_uuid=False), ForeignKey("mascota.id_mascota",     ondelete="CASCADE",   onupdate="CASCADE"), primary_key=True)
    rol_tutor:        Mapped[str]      = mapped_column(rol_tutor_enum, nullable=False, default="secundario")
    fecha_asignacion: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    tutor:   Mapped["UsuarioTutor"] = relationship("UsuarioTutor", back_populates="mascotas")
    mascota: Mapped["Mascota"]      = relationship("Mascota",      back_populates="tutores")


class CodigoAccesoMascota(Base):
    __tablename__ = "codigo_acceso_mascota"

    id_codigo:        Mapped[str]      = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    id_mascota:       Mapped[str]      = mapped_column(UUID(as_uuid=False), ForeignKey("mascota.id_mascota", ondelete="CASCADE", onupdate="CASCADE"), nullable=False)
    codigo:           Mapped[str]      = mapped_column(VARCHAR(20), nullable=False, unique=True)
    fecha_creacion:   Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    fecha_expiracion: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    usado:            Mapped[bool]     = mapped_column(Boolean, nullable=False, default=False)

    mascota: Mapped["Mascota"] = relationship("Mascota")

class Organizacion(Base):
    __tablename__ = "organizacion"

    id_organizacion: Mapped[str]      = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    rut:            Mapped[str]      = mapped_column(VARCHAR(20),  nullable=False, unique=True)
    fecha_registro: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
   


class Veterinario(Base):
    __tablename__ = "veterinario"

    id_veterinario:        Mapped[str]      = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    matricula:             Mapped[str]      = mapped_column(VARCHAR(50),  nullable=False, unique=True)
    nombre:                Mapped[str]      = mapped_column(VARCHAR(120), nullable=False)
    email:                 Mapped[str]      = mapped_column(VARCHAR(254), nullable=False, unique=True)
    password_hash:         Mapped[str]      = mapped_column(VARCHAR(255), nullable=False)
    estado:                Mapped[str]      = mapped_column(estado_general_enum, nullable=False, default="pendiente_verificacion")
    fecha_registro:        Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    id_organizacion:      Mapped[str|None] = mapped_column(UUID(as_uuid=False), ForeignKey("organizacion.id_organizacion", ondelete="SET NULL", onupdate="CASCADE"), nullable=True)
    
    consultas:              Mapped[list["Consulta"]]    = relationship("Consulta",    back_populates="veterinario")
    dosis:                  Mapped[list["Dosis"]]       = relationship("Dosis",       back_populates="veterinario")
    
    



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
    id_mascota:           Mapped[str]           = mapped_column(UUID(as_uuid=False), ForeignKey("mascota.id_mascota",        ondelete="CASCADE", onupdate="CASCADE"), nullable=False)
    id_veterinario:       Mapped[str]           = mapped_column(UUID(as_uuid=False), ForeignKey("veterinario.id_veterinario", ondelete="RESTRICT", onupdate="CASCADE"), nullable=False)
    fecha_hora:           Mapped[datetime]      = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    motivo:               Mapped[str]           = mapped_column(Text, nullable=False)
    diagnostico:          Mapped[str|None]      = mapped_column(Text, nullable=True)
    tratamiento_indicado: Mapped[str|None]      = mapped_column(Text, nullable=True)
    editado:              Mapped[bool]          = mapped_column(Boolean, nullable=False, default=False)
    fecha_edicion:        Mapped[datetime|None] = mapped_column(DateTime(timezone=True), nullable=True)

    mascota:     Mapped["Mascota"]     = relationship("Mascota",     back_populates="consultas")
    veterinario: Mapped["Veterinario"] = relationship("Veterinario", back_populates="consultas")


class Tratamiento(Base):
    __tablename__ = "tratamiento"
    __table_args__ = (
        UniqueConstraint("id_mascota", "nombre", name="uq_trat_nombre_mascota"),
        CheckConstraint("finalizacion IS NULL OR finalizacion >= inicio", name="chk_trat_fechas"),
    )

    id_tratamiento: Mapped[str]           = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    id_mascota:     Mapped[str]           = mapped_column(UUID(as_uuid=False), ForeignKey("mascota.id_mascota", ondelete="CASCADE", onupdate="CASCADE"), nullable=False)
    nombre:         Mapped[str]           = mapped_column(VARCHAR(150), nullable=False)
    descripcion:    Mapped[str|None]      = mapped_column(Text, nullable=True)
    frecuencia:     Mapped[str | None]    = mapped_column(VARCHAR(300), nullable=True)
    inicio:         Mapped[datetime]      = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    finalizacion:   Mapped[datetime|None] = mapped_column(DateTime(timezone=True), nullable=True)
    editado:        Mapped[bool]          = mapped_column(Boolean, nullable=False, default=False)
    fecha_edicion:  Mapped[datetime|None] = mapped_column(DateTime(timezone=True), nullable=True)

    mascota: Mapped["Mascota"] = relationship("Mascota", back_populates="tratamientos")
    
class TipoVacunas(Base):
    __tablename__ = "tipo_vacunas"

    id_vacuna:                  Mapped[str]      = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    nombre:                     Mapped[str]      = mapped_column(VARCHAR(120), nullable=False, unique=True)
    descripcion:                Mapped[str|None] = mapped_column(Text, nullable=True)
    especie_objetivo:           Mapped[str|None] = mapped_column(especie_enum, nullable=True)
    cantidad_dosis_requeridas:  Mapped[int]      = mapped_column(SmallInteger, nullable=False)
    intervalo_entre_dosis_dias: Mapped[int|None] = mapped_column(SmallInteger, nullable=True)
    activo:                     Mapped[bool]     = mapped_column(Boolean, nullable=False, default=True)
    esquemas_vacuna:            Mapped[list["EsquemaVacuna"]] = relationship("EsquemaVacuna",back_populates="tipo_vacuna")


class EsquemaVacunacion(Base):
    __tablename__ = "esquema_vacunacion"

    id_esquema: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    id_mascota: Mapped[str] = mapped_column(ForeignKey("mascota.id_mascota", ondelete="CASCADE"),nullable=False)
    fecha_inicio: Mapped[date] = mapped_column(Date, default=date.today)
    estado: Mapped[str] = mapped_column(estado_esquema_enum, default="activo")

    mascota: Mapped["Mascota"] = relationship("Mascota", back_populates="esquemas")
    vacunas: Mapped[list["EsquemaVacuna"]] = relationship("EsquemaVacuna", back_populates="esquema", cascade="all, delete-orphan",)

class EsquemaVacuna(Base):
    __tablename__ = "esquema_vacuna"

    id_esquema_vacuna: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    id_esquema: Mapped[str] = mapped_column(ForeignKey("esquema_vacunacion.id_esquema"), nullable=False)
    id_vacuna: Mapped[str] = mapped_column(ForeignKey("tipo_vacunas.id_vacuna"), nullable=False)

    estado: Mapped[str] = mapped_column(estado_esquema_enum, default="activo")
    fecha_proxima_dosis: Mapped[date | None] = mapped_column(Date)

    esquema: Mapped["EsquemaVacunacion"] = relationship("EsquemaVacunacion", back_populates="vacunas")
    tipo_vacuna: Mapped["TipoVacunas"] = relationship("TipoVacunas", back_populates="esquemas_vacuna")

    dosis: Mapped[list["Dosis"]] = relationship("Dosis", back_populates="esquema_vacuna", cascade="all, delete-orphan")


class Dosis(Base):
    __tablename__ = "dosis"

    id_dosis: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    id_esquema_vacuna: Mapped[str] = mapped_column(ForeignKey("esquema_vacuna.id_esquema_vacuna"), nullable=False)
    id_veterinario: Mapped[str] = mapped_column(ForeignKey("veterinario.id_veterinario"), nullable=False)

    numero_dosis: Mapped[int] = mapped_column(SmallInteger)
    fecha_aplicacion: Mapped[date] = mapped_column(Date)

    esquema_vacuna: Mapped["EsquemaVacuna"] = relationship("EsquemaVacuna", back_populates="dosis")
    veterinario: Mapped["Veterinario"] = relationship("Veterinario", back_populates="dosis")
    id_consulta: Mapped[str|None] = mapped_column(UUID(as_uuid=False),ForeignKey("consulta.id_consulta", ondelete="SET NULL", onupdate="CASCADE"),nullable=True)
    

class Pataporte(Base):
    __tablename__ = "pataporte"

    id_pataporte: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    id_mascota: Mapped[str] = mapped_column(ForeignKey("mascota.id_mascota", ondelete="CASCADE"), nullable=False)
    id_veterinario_emisor: Mapped[str] = mapped_column(ForeignKey("veterinario.id_veterinario", ondelete="RESTRICT"), nullable=False)
    hash_verificacion: Mapped[str] = mapped_column(VARCHAR(255), nullable=False)
    credencial_json: Mapped[str] = mapped_column(Text, nullable=False)
    fecha_emision: Mapped[date] = mapped_column(Date, default=date.today)
    estado: Mapped[str] = mapped_column(estado_cert_enum, default="vigente")



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
     expiracion:      Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
     usado:           Mapped[bool]     = mapped_column(Boolean, nullable=False, default=False)
     fecha_solicitud: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

     tutor: Mapped["UsuarioTutor"] = relationship("UsuarioTutor")

class VerificacionEmail(Base):
    """
    Guarda los códigos de verificación de correo enviados post-registro.
    Valida la activación de la cuenta tanto para Tutor como para Veterinario.
    """
    __tablename__ = "verificacion_email"

    id_verificacion: Mapped[str]      = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4()))
    email:           Mapped[str]      = mapped_column(VARCHAR(254), nullable=False)
    tipo_usuario:    Mapped[str]      = mapped_column(VARCHAR(20), nullable=False) # "tutor" | "veterinario"
    codigo_hash:     Mapped[str]      = mapped_column(VARCHAR(255), nullable=False)
    expiracion:      Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    usado:           Mapped[bool]     = mapped_column(Boolean, nullable=False, default=False)
    fecha_solicitud: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

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
    Base.metadata.create_all(bind=engine)

    # SEED INICIAL DE VACUNAS
    from sqlalchemy.orm import Session

    db = SessionLocal()
    try:
        # si ya hay vacunas, no insertar de nuevo
        existe = db.query(TipoVacunas).first()
        if existe:
            return

        vacunas_base = [
            TipoVacunas(
                nombre="Antirrábica canina",
                descripcion="Prevención de rabia en perros",
                especie_objetivo="perro",
                cantidad_dosis_requeridas=1,
                intervalo_entre_dosis_dias=None,
                activo=True,
            ),
            TipoVacunas(
                nombre="Antirrábica felina",
                descripcion="Prevención de rabia en gatos",
                especie_objetivo="gato",
                cantidad_dosis_requeridas=1,
                intervalo_entre_dosis_dias=None,
                activo=True,
            ),
            TipoVacunas(
                nombre="Moquillo",
                descripcion="Distemper canino",
                especie_objetivo="perro",
                cantidad_dosis_requeridas=3,
                intervalo_entre_dosis_dias=30,
                activo=True,
            ),
            TipoVacunas(
                nombre="Parvovirus",
                descripcion="Protección contra parvovirus",
                especie_objetivo="perro",
                cantidad_dosis_requeridas=3,
                intervalo_entre_dosis_dias=30,
                activo=True,
            ),
            TipoVacunas(
                nombre="Triple felina",
                descripcion="Rinotraqueitis + Calicivirus + Panleucopenia",
                especie_objetivo="gato",
                cantidad_dosis_requeridas=2,
                intervalo_entre_dosis_dias=30,
                activo=True,
            ),
        ]

        db.add_all(vacunas_base)
        db.commit()

    finally:
        db.close()