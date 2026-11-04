"""Catálogo inicial de vacunas; conserva filas previas con el mismo nombre."""
from uuid import NAMESPACE_URL, uuid5

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert, UUID

revision = "0002_seed_vaccines"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None

VACCINES = [
    ("Antirrábica canina", "Prevención de rabia en perros", "perro", 1, None),
    ("Antirrábica felina", "Prevención de rabia en gatos", "gato", 1, None),
    ("Moquillo", "Distemper canino", "perro", 3, 30),
    ("Parvovirus", "Protección contra parvovirus", "perro", 3, 30),
    ("Triple felina", "Rinotraqueitis + Calicivirus + Panleucopenia", "gato", 2, 30),
]


def vaccine_id(name):
    return str(uuid5(NAMESPACE_URL, "pataporte:initial-vaccine:" + name))


def table():
    return sa.table(
        "tipo_vacunas", sa.column("id_vacuna", UUID(as_uuid=False)),
        sa.column("nombre", sa.String()), sa.column("descripcion", sa.Text()),
        sa.column("especie_objetivo", sa.String()),
        sa.column("cantidad_dosis_requeridas", sa.SmallInteger()),
        sa.column("intervalo_entre_dosis_dias", sa.SmallInteger()),
        sa.column("activo", sa.Boolean()),
    )


def upgrade():
    rows = [dict(id_vacuna=vaccine_id(name), nombre=name, descripcion=description,
                 especie_objetivo=species, cantidad_dosis_requeridas=doses,
                 intervalo_entre_dosis_dias=interval, activo=True)
            for name, description, species, doses, interval in VACCINES]
    op.execute(insert(table()).values(rows).on_conflict_do_nothing(index_elements=["nombre"]))


def downgrade():
    vaccines = table()
    # Solo IDs de este seed; las FK impiden borrar vacunas que ya están en uso.
    op.execute(vaccines.delete().where(vaccines.c.id_vacuna.in_([vaccine_id(x[0]) for x in VACCINES])))
