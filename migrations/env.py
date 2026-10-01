from alembic import context
from backend import models  # Register every model in the metadata.
from core.database import Base, engine

target_metadata = Base.metadata

if context.is_offline_mode():
    context.configure(
        url=engine.url, target_metadata=target_metadata,
        literal_binds=True, dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()
else:
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()
