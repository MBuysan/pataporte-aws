from logging.config import fileConfig

from alembic import context

from config.database import Base, engine

config = context.config
if config.config_file_name:
    fileConfig(config.config_file_name, disable_existing_loggers=False)

# ponytail: solo modo online (con conexión); agregar modo offline si hace falta generar SQL a mano.
with engine.connect() as connection:
    context.configure(connection=connection, target_metadata=Base.metadata, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()
