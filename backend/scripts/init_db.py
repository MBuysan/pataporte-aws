"""
Crea las tablas y carga el seed de tipos de vacunas. Es idempotente.
Se corre como tarea one-off antes de cada deploy:  python -m scripts.init_db

ponytail: create_all solo crea tablas que faltan, no altera las existentes.
Si el esquema cambia y hay que conservar datos, el camino es Alembic (ya está en requirements).
"""
from config.database import Base, SessionLocal, TipoVacunas, engine


def init_db():
    Base.metadata.create_all(bind=engine)

    # SEED INICIAL DE VACUNAS
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


if __name__ == "__main__":
    init_db()
    print("init_db: tablas y seed OK")
