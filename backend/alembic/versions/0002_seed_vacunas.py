"""seed de tipos de vacunas (idempotente: no pisa filas con el mismo nombre)

Revision ID: 0002
Revises: 0001
"""
from uuid import NAMESPACE_URL, uuid5

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, insert

revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None

# nombre, descripcion, especie_objetivo, cantidad_dosis_requeridas, intervalo_entre_dosis_dias
VACUNAS = [
    ("Antirrábica canina", "Prevención de rabia en perros", "perro", 1, None),
    ("Antirrábica felina", "Prevención de rabia en gatos", "gato", 1, None),
    ("Moquillo", "Distemper canino", "perro", 3, 30),
    ("Parvovirus", "Protección contra parvovirus", "perro", 3, 30),
    ("Triple felina", "Rinotraqueitis + Calicivirus + Panleucopenia", "gato", 2, 30),
]

tipo_vacunas = sa.table(
    "tipo_vacunas",
    sa.column("id_vacuna", UUID(as_uuid=False)),
    sa.column("nombre", sa.String()),
    sa.column("descripcion", sa.Text()),
    sa.column("especie_objetivo", sa.Enum("perro", "gato", "otro", name="especie", create_type=False)),
    sa.column("cantidad_dosis_requeridas", sa.SmallInteger()),
    sa.column("intervalo_entre_dosis_dias", sa.SmallInteger()),
    sa.column("activo", sa.Boolean()),
)


def _id(nombre):
    # id estable: el mismo seed da el mismo id en cualquier base
    return str(uuid5(NAMESPACE_URL, "pataporte:vacuna:" + nombre))


def upgrade():
    filas = [
        dict(id_vacuna=_id(n), nombre=n, descripcion=d, especie_objetivo=e,
             cantidad_dosis_requeridas=c, intervalo_entre_dosis_dias=i, activo=True)
        for n, d, e, c, i in VACUNAS
    ]
    op.execute(insert(tipo_vacunas).values(filas).on_conflict_do_nothing(index_elements=["nombre"]))


def downgrade():
    # solo las filas de este seed; la FK impide borrar vacunas ya usadas
    op.execute(tipo_vacunas.delete().where(tipo_vacunas.c.id_vacuna.in_([_id(v[0]) for v in VACUNAS])))
