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
        if connection.dialect.name == "sqlite":
            # Batch table rebuilds require FK checks disabled outside a transaction.
            # Explicit BEGIN makes SQLite DDL rollback together on any failure.
            connection.exec_driver_sql("PRAGMA foreign_keys=OFF")
            connection.commit()
            try:
                connection.exec_driver_sql("BEGIN IMMEDIATE")
                context.configure(connection=connection, target_metadata=target_metadata, render_as_batch=True, transactional_ddl=True)
                with context.begin_transaction():
                    context.run_migrations()
                if connection.exec_driver_sql("PRAGMA foreign_key_check").fetchall():
                    raise RuntimeError("Migration violates foreign keys; restore/check source data")
                connection.commit()
            except Exception:
                connection.rollback()
                raise
            finally:
                connection.exec_driver_sql("PRAGMA foreign_keys=ON")
                connection.commit()
        else:
            context.configure(connection=connection, target_metadata=target_metadata)
            with context.begin_transaction():
                context.run_migrations()
