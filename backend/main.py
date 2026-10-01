from backend.api.router import router as api_router
from backend.models import HotelService, Role, Room, RoomStatus, RoomType, User
from backend.web.routes import router as web_router
from contextlib import asynccontextmanager
from core.config import FRONTEND_DIR, settings
from core.database import Base, SessionLocal, engine
from core.security import hash_password
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        if not db.scalar(select(User.id).limit(1)):
            db.add(User(username="admin", full_name="Quản trị viên", password_hash=hash_password("Admin@123"), role=Role.admin))
            db.commit()
        if not db.scalar(select(RoomType.id).limit(1)):
            deluxe = RoomType(name="Deluxe City View", capacity=2, nightly_rate=980000, amenities="Giường King · Bồn tắm · City view")
            family = RoomType(name="Family Suite", capacity=4, nightly_rate=1650000, amenities="2 phòng ngủ · Bếp nhỏ · Ban công")
            db.add_all([deluxe, family]); db.flush()
            db.add_all([
                Room(number="201", floor=2, room_type_id=deluxe.id, status=RoomStatus.available),
                Room(number="202", floor=2, room_type_id=deluxe.id, status=RoomStatus.occupied),
                Room(number="301", floor=3, room_type_id=family.id, status=RoomStatus.cleaning),
                Room(number="302", floor=3, room_type_id=family.id, status=RoomStatus.available),
            ])
            db.add_all([HotelService(name="Giặt là", unit="kg", price=50000), HotelService(name="Đưa đón sân bay", unit="chuyến", price=350000), HotelService(name="Ăn sáng", unit="suất", price=180000)])
            db.commit()
    yield

app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.mount("/static", StaticFiles(directory=FRONTEND_DIR / "static"), name="static")
app.include_router(api_router)
app.include_router(web_router)

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Send browser pages to login while preserving JSON errors for the API."""
    if exc.status_code == 401 and not request.url.path.startswith("/api/"):
        return RedirectResponse(url=f"/login?next={request.url.path}", status_code=303)
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail}, headers=exc.headers)
