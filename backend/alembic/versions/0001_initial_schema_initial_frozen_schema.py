"""Initial frozen schema

Revision ID: 0001_initial_schema
Revises: None
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = '0001_initial_schema'
down_revision = None
branch_labels = None
depends_on = None

ENUMS = {
    'sexo_mascota': ('macho', 'hembra', 'desconocido',),
    'especie': ('perro', 'gato', 'otro',),
    'estado_general': ('activo', 'inactivo', 'pendiente_verificacion',),
    'rol_tutor': ('principal', 'secundario',),
    'estado_esquema': ('activo', 'completado',),
    'estado_pataporte': ('vigente', 'deprecado', 'revocado',),
}


def enum_type(name):
    return postgresql.ENUM(*ENUMS[name], name=name, create_type=False)


def upgrade():
    for name in ENUMS:
        enum_type(name).create(op.get_bind(), checkfirst=False)
    op.create_table('mascota',
    sa.Column('id_mascota', sa.UUID(as_uuid=False), nullable=False),
    sa.Column('nombre', sa.VARCHAR(length=100), nullable=False),
    sa.Column('fecha_de_nacimiento', sa.Date(), nullable=True),
    sa.Column('sexo', enum_type('sexo_mascota'), nullable=False),
    sa.Column('especie', enum_type('especie'), nullable=False),
    sa.Column('raza', sa.VARCHAR(length=60), nullable=True),
    sa.Column('foto_url', sa.Text(), nullable=True),
    sa.Column('fecha_registro', sa.DateTime(timezone=True), nullable=False),
    sa.Column('estado', enum_type('estado_general'), nullable=False),
    sa.PrimaryKeyConstraint('id_mascota')
    )
    op.create_table('organizacion',
    sa.Column('id_organizacion', sa.UUID(as_uuid=False), nullable=False),
    sa.Column('rut', sa.VARCHAR(length=20), nullable=False),
    sa.Column('fecha_registro', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id_organizacion'),
    sa.UniqueConstraint('rut')
    )
    op.create_table('tipo_vacunas',
    sa.Column('id_vacuna', sa.UUID(as_uuid=False), nullable=False),
    sa.Column('nombre', sa.VARCHAR(length=120), nullable=False),
    sa.Column('descripcion', sa.Text(), nullable=True),
    sa.Column('especie_objetivo', enum_type('especie'), nullable=True),
    sa.Column('cantidad_dosis_requeridas', sa.SmallInteger(), nullable=False),
    sa.Column('intervalo_entre_dosis_dias', sa.SmallInteger(), nullable=True),
    sa.Column('activo', sa.Boolean(), nullable=False),
    sa.PrimaryKeyConstraint('id_vacuna'),
    sa.UniqueConstraint('nombre')
    )
    op.create_table('usuario_tutor',
    sa.Column('id_tutor', sa.UUID(as_uuid=False), nullable=False),
    sa.Column('cedula', sa.VARCHAR(length=20), nullable=False),
    sa.Column('nombre', sa.VARCHAR(length=120), nullable=False),
    sa.Column('rol_tutor', enum_type('rol_tutor'), nullable=False),
    sa.Column('email', sa.VARCHAR(length=254), nullable=False),
    sa.Column('telefono', sa.VARCHAR(length=30), nullable=True),
    sa.Column('password_hash', sa.VARCHAR(length=255), nullable=False),
    sa.Column('fecha_registro', sa.DateTime(timezone=True), nullable=False),
    sa.Column('estado', enum_type('estado_general'), nullable=False),
    sa.PrimaryKeyConstraint('id_tutor'),
    sa.UniqueConstraint('cedula'),
    sa.UniqueConstraint('email')
    )
    op.create_table('verificacion_email',
    sa.Column('id_verificacion', sa.UUID(as_uuid=False), nullable=False),
    sa.Column('email', sa.VARCHAR(length=254), nullable=False),
    sa.Column('tipo_usuario', sa.VARCHAR(length=20), nullable=False),
    sa.Column('codigo_hash', sa.VARCHAR(length=255), nullable=False),
    sa.Column('expiracion', sa.DateTime(timezone=True), nullable=False),
    sa.Column('usado', sa.Boolean(), nullable=False),
    sa.Column('fecha_solicitud', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id_verificacion')
    )
    op.create_table('codigo_acceso_mascota',
    sa.Column('id_codigo', sa.UUID(as_uuid=False), nullable=False),
    sa.Column('id_mascota', sa.UUID(as_uuid=False), nullable=False),
    sa.Column('codigo', sa.VARCHAR(length=20), nullable=False),
    sa.Column('fecha_creacion', sa.DateTime(timezone=True), nullable=False),
    sa.Column('fecha_expiracion', sa.DateTime(timezone=True), nullable=False),
    sa.Column('usado', sa.Boolean(), nullable=False),
    sa.ForeignKeyConstraint(['id_mascota'], ['mascota.id_mascota'], onupdate='CASCADE', ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id_codigo'),
    sa.UniqueConstraint('codigo')
    )
    op.create_table('esquema_vacunacion',
    sa.Column('id_esquema', sa.UUID(as_uuid=False), nullable=False),
    sa.Column('id_mascota', sa.UUID(as_uuid=False), nullable=False),
    sa.Column('fecha_inicio', sa.Date(), nullable=False),
    sa.Column('estado', enum_type('estado_esquema'), nullable=False),
    sa.ForeignKeyConstraint(['id_mascota'], ['mascota.id_mascota'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id_esquema')
    )
    op.create_table('mascota_tutor',
    sa.Column('id_tutor', sa.UUID(as_uuid=False), nullable=False),
    sa.Column('id_mascota', sa.UUID(as_uuid=False), nullable=False),
    sa.Column('rol_tutor', enum_type('rol_tutor'), nullable=False),
    sa.Column('fecha_asignacion', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['id_mascota'], ['mascota.id_mascota'], onupdate='CASCADE', ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['id_tutor'], ['usuario_tutor.id_tutor'], onupdate='CASCADE', ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id_tutor', 'id_mascota')
    )
    op.create_table('pataporte',
    sa.Column('id_pataporte', sa.UUID(as_uuid=False), nullable=False),
    sa.Column('id_mascota', sa.UUID(as_uuid=False), nullable=False),
    sa.Column('emitido_por_rol', sa.VARCHAR(length=20), nullable=False),
    sa.Column('emitido_por_id', sa.UUID(as_uuid=False), nullable=False),
    sa.Column('hash_verificacion', sa.VARCHAR(length=255), nullable=False),
    sa.Column('credencial_json', sa.Text(), nullable=False),
    sa.Column('fecha_emision', sa.Date(), nullable=False),
    sa.Column('estado', enum_type('estado_pataporte'), nullable=False),
    sa.ForeignKeyConstraint(['id_mascota'], ['mascota.id_mascota'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id_pataporte'),
    sa.UniqueConstraint('hash_verificacion'),
    sa.UniqueConstraint('hash_verificacion', name='uq_pataporte_hash')
    )
    op.create_table('recuperacion_password',
    sa.Column('id_recuperacion', sa.UUID(as_uuid=False), nullable=False),
    sa.Column('id_tutor', sa.UUID(as_uuid=False), nullable=False),
    sa.Column('codigo_hash', sa.VARCHAR(length=255), nullable=False),
    sa.Column('expiracion', sa.DateTime(timezone=True), nullable=False),
    sa.Column('usado', sa.Boolean(), nullable=False),
    sa.Column('fecha_solicitud', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['id_tutor'], ['usuario_tutor.id_tutor'], onupdate='CASCADE', ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id_recuperacion')
    )
    op.create_table('tratamiento',
    sa.Column('id_tratamiento', sa.UUID(as_uuid=False), nullable=False),
    sa.Column('id_mascota', sa.UUID(as_uuid=False), nullable=False),
    sa.Column('nombre', sa.VARCHAR(length=150), nullable=False),
    sa.Column('descripcion', sa.Text(), nullable=True),
    sa.Column('frecuencia', sa.VARCHAR(length=300), nullable=True),
    sa.Column('inicio', sa.DateTime(timezone=True), nullable=False),
    sa.Column('finalizacion', sa.DateTime(timezone=True), nullable=True),
    sa.Column('editado', sa.Boolean(), nullable=False),
    sa.Column('fecha_edicion', sa.DateTime(timezone=True), nullable=True),
    sa.CheckConstraint('finalizacion IS NULL OR finalizacion >= inicio', name='chk_trat_fechas'),
    sa.ForeignKeyConstraint(['id_mascota'], ['mascota.id_mascota'], onupdate='CASCADE', ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id_tratamiento'),
    sa.UniqueConstraint('id_mascota', 'nombre', name='uq_trat_nombre_mascota')
    )
    op.create_table('veterinario',
    sa.Column('id_veterinario', sa.UUID(as_uuid=False), nullable=False),
    sa.Column('matricula', sa.VARCHAR(length=50), nullable=False),
    sa.Column('nombre', sa.VARCHAR(length=120), nullable=False),
    sa.Column('email', sa.VARCHAR(length=254), nullable=False),
    sa.Column('password_hash', sa.VARCHAR(length=255), nullable=False),
    sa.Column('estado', enum_type('estado_general'), nullable=False),
    sa.Column('fecha_registro', sa.DateTime(timezone=True), nullable=False),
    sa.Column('id_organizacion', sa.UUID(as_uuid=False), nullable=False),
    sa.ForeignKeyConstraint(['id_organizacion'], ['organizacion.id_organizacion'], onupdate='CASCADE', ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id_veterinario'),
    sa.UniqueConstraint('email'),
    sa.UniqueConstraint('matricula')
    )
    op.create_table('consulta',
    sa.Column('id_consulta', sa.UUID(as_uuid=False), nullable=False),
    sa.Column('id_mascota', sa.UUID(as_uuid=False), nullable=False),
    sa.Column('id_veterinario', sa.UUID(as_uuid=False), nullable=False),
    sa.Column('fecha_hora', sa.DateTime(timezone=True), nullable=False),
    sa.Column('motivo', sa.Text(), nullable=False),
    sa.Column('diagnostico', sa.Text(), nullable=True),
    sa.Column('tratamiento_indicado', sa.Text(), nullable=True),
    sa.Column('editado', sa.Boolean(), nullable=False),
    sa.Column('fecha_edicion', sa.DateTime(timezone=True), nullable=True),
    sa.CheckConstraint('(editado = FALSE AND fecha_edicion IS NULL) OR (editado = TRUE AND fecha_edicion IS NOT NULL)', name='chk_edicion'),
    sa.ForeignKeyConstraint(['id_mascota'], ['mascota.id_mascota'], onupdate='CASCADE', ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['id_veterinario'], ['veterinario.id_veterinario'], onupdate='CASCADE', ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id_consulta')
    )
    op.create_table('esquema_vacuna',
    sa.Column('id_esquema_vacuna', sa.UUID(as_uuid=False), nullable=False),
    sa.Column('id_esquema', sa.UUID(as_uuid=False), nullable=False),
    sa.Column('id_vacuna', sa.UUID(as_uuid=False), nullable=False),
    sa.Column('estado', enum_type('estado_esquema'), nullable=False),
    sa.Column('fecha_proxima_dosis', sa.Date(), nullable=True),
    sa.ForeignKeyConstraint(['id_esquema'], ['esquema_vacunacion.id_esquema'], ),
    sa.ForeignKeyConstraint(['id_vacuna'], ['tipo_vacunas.id_vacuna'], ),
    sa.PrimaryKeyConstraint('id_esquema_vacuna')
    )
    op.create_table('dosis',
    sa.Column('id_dosis', sa.UUID(as_uuid=False), nullable=False),
    sa.Column('id_esquema_vacuna', sa.UUID(as_uuid=False), nullable=False),
    sa.Column('id_veterinario', sa.UUID(as_uuid=False), nullable=False),
    sa.Column('numero_dosis', sa.SmallInteger(), nullable=False),
    sa.Column('fecha_aplicacion', sa.Date(), nullable=False),
    sa.Column('id_consulta', sa.UUID(as_uuid=False), nullable=True),
    sa.ForeignKeyConstraint(['id_consulta'], ['consulta.id_consulta'], onupdate='CASCADE', ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['id_esquema_vacuna'], ['esquema_vacuna.id_esquema_vacuna'], ),
    sa.ForeignKeyConstraint(['id_veterinario'], ['veterinario.id_veterinario'], ),
    sa.PrimaryKeyConstraint('id_dosis')
    )


def downgrade():
    op.drop_table('dosis')
    op.drop_table('esquema_vacuna')
    op.drop_table('consulta')
    op.drop_table('veterinario')
    op.drop_table('tratamiento')
    op.drop_table('recuperacion_password')
    op.drop_table('pataporte')
    op.drop_table('mascota_tutor')
    op.drop_table('esquema_vacunacion')
    op.drop_table('codigo_acceso_mascota')
    op.drop_table('verificacion_email')
    op.drop_table('usuario_tutor')
    op.drop_table('tipo_vacunas')
    op.drop_table('organizacion')
    op.drop_table('mascota')
    for name in reversed(ENUMS):
        enum_type(name).drop(op.get_bind(), checkfirst=False)
