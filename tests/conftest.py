import os
os.environ["DATABASE_URL"] = "sqlite:///./test_hotel.db"
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base, get_db
from app.main import app
from app.auth import hash_password
from app.models import User, Role, RoomType, Room, Customer, HotelService


engine = create_engine("sqlite:///./test_hotel.db", connect_args={"check_same_thread": False})
TestingSession = sessionmaker(bind=engine)


@pytest.fixture()
def db():
    Base.metadata.drop_all(engine); Base.metadata.create_all(engine)
    with TestingSession() as session:
        session.add_all([User(username="admin", full_name="Admin", password_hash=hash_password("Admin@123"), role=Role.admin), RoomType(id=1,name="Deluxe",capacity=2,nightly_rate=900000,amenities="Bồn tắm"), Room(id=1,number="302",floor=3,room_type_id=1), Customer(id=1,full_name="Nguyễn An",phone="0900000000"), HotelService(id=1,name="Giặt là",unit="kg",price=50000)]); session.commit(); yield session


@pytest.fixture()
def client(db):
    def override(): yield db
    app.dependency_overrides[get_db] = override
    with TestClient(app) as c:
        c.post("/login", data={"username":"admin","password":"Admin@123"})
        yield c
    app.dependency_overrides.clear()

