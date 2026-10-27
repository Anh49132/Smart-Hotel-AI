from backend.api.router import router as api_router
from backend.models import HotelService, Role, Room, RoomStatus, RoomType, User
from backend.web.routes import router as web_router
from contextlib import asynccontextmanager
from core.config import FRONTEND_DIR, settings
from core.database import Base, SessionLocal, engine
from core.security import hash_password, verify_password
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select,text
from core.body_limit import RequestBodyLimit

@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.auto_create_schema:
        Base.metadata.create_all(engine)
    with SessionLocal() as db:
        if not db.scalar(select(User.id).limit(1)):
            initial_password = settings.bootstrap_admin_password.get_secret_value()
            if not initial_password and settings.app_env == 'production':
                raise RuntimeError('Set BOOTSTRAP_ADMIN_PASSWORD for the first production startup')
            db.add(User(username="admin", full_name="Quản trị viên", password_hash=hash_password(initial_password or "Admin@123"), role=Role.admin, must_change_password=True))
            db.commit()
        if settings.app_env == 'production':
            for account in db.scalars(select(User).where(User.is_active.is_(True))):
                if verify_password('Admin@123', account.password_hash):
                    raise RuntimeError('Change sample account passwords before production startup')
        if settings.demo_mode:
            from backend.services.demo_service import extend_existing_demo_months,seed_demo
            result=seed_demo(db,settings.demo_staff_password.get_secret_value()) if settings.demo_seed_on_start else extend_existing_demo_months(db)
            if result is not None:
                print(f"Demo seed complete: already_seeded={result['already_seeded']} monthly_bookings_added={result.get('monthly_bookings_added',0)}",flush=True)
        if settings.seed_demo_data and not settings.demo_mode and not db.scalar(select(RoomType.id).limit(1)):
            deluxe = RoomType(name="Deluxe City View", capacity=2, nightly_rate=980000, amenities="Giường King · Bồn tắm · City view")
            family = RoomType(name="Family Suite", capacity=4, nightly_rate=1650000, amenities="2 phòng ngủ · Bếp nhỏ · Ban công")
            db.add_all([deluxe, family]); db.flush()
            db.add_all([
                Room(number="201", floor=2, room_type_id=deluxe.id, status=RoomStatus.available),
                Room(number="202", floor=2, room_type_id=deluxe.id, status=RoomStatus.available),
                Room(number="301", floor=3, room_type_id=family.id, status=RoomStatus.available),
                Room(number="302", floor=3, room_type_id=family.id, status=RoomStatus.available),
            ])
            db.add_all([HotelService(name="Giặt là", unit="kg", price=50000), HotelService(name="Đưa đón sân bay", unit="chuyến", price=350000), HotelService(name="Ăn sáng", unit="suất", price=180000)])
            db.commit()
    try:yield
    finally:engine.dispose()

app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.add_middleware(RequestBodyLimit)
app.mount("/static", StaticFiles(directory=FRONTEND_DIR / "static"), name="static")
app.include_router(api_router)
app.include_router(web_router)

@app.get('/healthz',include_in_schema=False)
def health():
    try:
        with engine.connect() as db:db.execute(text('SELECT 1'))
    except Exception:return JSONResponse({'status':'unavailable'},status_code=503,headers={'Cache-Control':'no-store'})
    return JSONResponse({'status':'ok'},headers={'Cache-Control':'no-store'})


@app.middleware('http')
async def protect_cookie_requests(request: Request, call_next):
    if request.method in ('POST', 'PUT', 'PATCH', 'DELETE'):
        origin = request.headers.get('origin')
        expected = str(request.base_url).rstrip('/')
        if origin and origin != expected:
            return JSONResponse({'detail': 'Nguồn yêu cầu không hợp lệ'}, status_code=403)
        if request.url.path.startswith('/api/') and request.cookies.get('access_token'):
            content_type = request.headers.get('content-type', '').split(';')[0]
            if content_type in ('application/x-www-form-urlencoded', 'multipart/form-data', 'text/plain'):
                return JSONResponse({'detail': 'API yêu cầu nội dung JSON'}, status_code=403)
    return await call_next(request)

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Send browser pages to login while preserving JSON errors for the API."""
    if exc.status_code == 401 and not request.url.path.startswith("/api/"):
        return RedirectResponse(url=f"/login?next={request.url.path}", status_code=303)
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail}, headers=exc.headers)
