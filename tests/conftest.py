import os
from tempfile import TemporaryDirectory
from pathlib import Path
from uuid import uuid4
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

_test_directory = TemporaryDirectory(prefix="hotel-tests-")
_pg_admin = None
_pg_schema = None
if os.environ.get("HOTEL_TEST_DATABASE_URL"):
    _url = make_url(os.environ["HOTEL_TEST_DATABASE_URL"])
    if _url.drivername in ("postgres", "postgresql"):
        _url = _url.set(drivername="postgresql+psycopg")
    if _url.get_backend_name() != "postgresql":
        raise ValueError("HOTEL_TEST_DATABASE_URL must be PostgreSQL")
    _pg_admin = create_engine(_url)
    _pg_schema = "hotel_test_" + uuid4().hex
    with _pg_admin.begin() as _connection:
        _connection.execute(text(f'CREATE SCHEMA "{_pg_schema}"'))
    _url = _url.update_query_dict({"options": f"-csearch_path={_pg_schema}"})
    os.environ["DATABASE_URL"] = _url.render_as_string(hide_password=False)
else:
    os.environ["DATABASE_URL"] = f"sqlite:///{(Path(_test_directory.name) / 'hotel.db').as_posix()}"
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker
from core.database import Base, get_db, engine
from backend.main import app
from core.security import hash_password
from backend.models import User, Role, RoomType, Room, Customer, HotelService


TestingSession = sessionmaker(bind=engine)


@pytest.fixture()
def db(monkeypatch):
    from datetime import datetime, timedelta, timezone
    fixed_now=lambda:datetime(2030,1,10,15,tzinfo=timezone(timedelta(hours=7)))
    monkeypatch.setattr('core.hotel_time.hotel_now',fixed_now)
    monkeypatch.setattr('backend.services.frontdesk_service.hotel_now',fixed_now)
    # Recreating PostgreSQL enums changes their OIDs; discard pooled prepared plans.
    engine.dispose()
    Base.metadata.drop_all(engine); Base.metadata.create_all(engine)
    with TestingSession() as session:
        session.add_all([User(username="admin", full_name="Admin", password_hash=hash_password("Admin@123"), role=Role.admin), RoomType(id=1,name="Deluxe",capacity=2,nightly_rate=900000,amenities="Bồn tắm"), Room(id=1,number="302",floor=3,room_type_id=1), Customer(id=1,full_name="Nguyễn An",phone="0900000000"), HotelService(id=1,name="Giặt là",unit="kg",price=50000)]); session.commit()
        if engine.dialect.name == 'postgresql':
            for table in ('room_types','rooms','customers','services'):
                session.execute(text(f"SELECT setval(pg_get_serial_sequence('{table}','id'), COALESCE((SELECT MAX(id) FROM {table}),1), true)"))
            session.commit()
        yield session


@pytest.fixture()
def client(db):
    from core.login_limiter import login_limiter
    login_limiter.entries.clear()
    from core.ai_limiter import ai_budget
    ai_budget.entries.clear()
    def override(): yield db
    app.dependency_overrides[get_db] = override
    with TestClient(app) as c:
        c.post("/login", data={"username":"admin","password":"Admin@123"})
        yield c
    app.dependency_overrides.clear()






def pytest_sessionfinish(session, exitstatus):
    import gc
    gc.collect()  # Finalize request generators before Windows removes SQLite files.
    engine.dispose()
    if _pg_admin is not None:
        with _pg_admin.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{_pg_schema}" CASCADE'))
        _pg_admin.dispose()
    _test_directory.cleanup()
