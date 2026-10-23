from .config import settings
from .db_engine import build_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

engine = build_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
