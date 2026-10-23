"""Database URL handling shared by the app and offline migration tools."""
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.engine import make_url

from core.config import PROJECT_ROOT


def normalize_database_url(value):
    url = make_url(value)
    if url.drivername in ("postgres", "postgresql"):
        url = url.set(drivername="postgresql+psycopg")
    if url.get_backend_name() == "sqlite" and url.database not in (None, "", ":memory:"):
        path = Path(url.database)
        if not path.is_absolute():
            path = PROJECT_ROOT / path
        url = url.set(database=str(path.resolve()))
    return url


def build_engine(value):
    url = normalize_database_url(value)
    options = {"pool_pre_ping": True}
    if url.get_backend_name() == "sqlite":
        if url.database not in (None, "", ":memory:"):
            Path(url.database).parent.mkdir(parents=True, exist_ok=True)
        options["connect_args"] = {"check_same_thread": False, "timeout": 15}
    else:
        options.update(pool_size=3, max_overflow=2, pool_timeout=10)
        if url.get_backend_name() == "postgresql":
            options["connect_args"] = {"connect_timeout": 10}
            # Render's private host has no dots. Public connections require TLS.
            if url.host and url.host not in ("localhost", "127.0.0.1", "::1") and "." in url.host and "sslmode" not in url.query:
                options["connect_args"]["sslmode"] = "require"
    engine = create_engine(url, **options)
    if url.get_backend_name() == "sqlite":
        @event.listens_for(engine, "connect")
        def enforce_foreign_keys(connection, _):
            previous = getattr(connection, "autocommit", None)
            if previous is not None:
                connection.autocommit = True
            cursor = connection.cursor()
            try:
                cursor.execute("PRAGMA foreign_keys=ON")
            finally:
                cursor.close()
                if previous is not None:
                    connection.autocommit = previous
    return engine
