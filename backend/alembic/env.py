from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

from config.db_connection import DatabaseSettings
from config.models import Base

config = context.config
if config.config_file_name:
    fileConfig(config.config_file_name)
target_metadata = Base.metadata


def run_online(connection):
    context.configure(connection=connection, target_metadata=target_metadata,
                      compare_type=True, compare_server_default=False)
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    context.configure(url="postgresql://", target_metadata=target_metadata,
                      literal_binds=True, dialect_opts={"paramstyle": "named"})
    with context.begin_transaction():
        context.run_migrations()
elif config.attributes.get("connection") is not None:
    run_online(config.attributes["connection"])
else:
    settings = DatabaseSettings()
    engine = create_engine(settings.sqlalchemy_url(), poolclass=pool.NullPool,
                           connect_args=settings.database_connect_args())
    with engine.connect() as connection:
        run_online(connection)
    engine.dispose()
