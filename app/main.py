from contextlib import asynccontextmanager
from datetime import date, datetime
from pathlib import Path
from calendar import monthrange
from fastapi import Depends, FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload
from .auth import authenticate, create_token, get_current_user, hash_password, require_roles
from .config import settings
from .database import Base, SessionLocal, engine, get_db
from .models import Booking, BookingStatus, Customer, HotelService, Invoice, Role, Room, RoomStatus, RoomType, User
from .routers.api import router as api_router


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
ROOT = Path(__file__).parent
app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
templates = Jinja2Templates(directory=ROOT / "templates")
STATUS_LABELS = {
    "available": "Trống", "occupied": "Đang ở", "cleaning": "Đang dọn", "maintenance": "Bảo trì",
    "confirmed": "Đã xác nhận", "checked_in": "Đang lưu trú", "checked_out": "Đã trả phòng", "cancelled": "Đã hủy",
    "unpaid": "Chưa thanh toán", "partial": "Thanh toán một phần", "paid": "Đã thanh toán",
}
templates.env.globals["status_label"] = lambda value: STATUS_LABELS.get(getattr(value, "value", value), getattr(value, "value", value))
app.include_router(api_router)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Send browser pages to login while preserving JSON errors for the API."""
    if exc.status_code == 401 and not request.url.path.startswith("/api/"):
        return RedirectResponse(url=f"/login?next={request.url.path}", status_code=303)
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail}, headers=exc.headers)


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request): return templates.TemplateResponse("login.html", {"request": request})


@app.post("/login")
def login(request: Request, username: str = Form(), password: str = Form(), db: Session = Depends(get_db)):
    user = authenticate(db, username, password)
    if not user: return templates.TemplateResponse("login.html", {"request": request, "error": "Sai tên đăng nhập hoặc mật khẩu"}, status_code=401)
    response = RedirectResponse("/", 303); response.set_cookie("access_token", create_token(user), httponly=True, samesite="lax"); return response


@app.get("/logout")
def logout():
    response = RedirectResponse("/login", 303); response.delete_cookie("access_token"); return response


def page_context(request, user, active, **extra): return {"request": request, "user": user, "active": active, **extra}


@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request, user=Depends(get_current_user), db: Session = Depends(get_db)):
    stats = {"rooms": db.scalar(select(func.count(Room.id))) or 0, "available": db.scalar(select(func.count(Room.id)).where(Room.status == RoomStatus.available)) or 0, "today": db.scalar(select(func.count(Booking.id)).where(Booking.check_in == date.today())) or 0, "revenue": db.scalar(select(func.coalesce(func.sum(Invoice.paid_amount), 0))) or 0}
    stats["occupancy"] = round((stats["rooms"] - stats["available"]) / stats["rooms"] * 100) if stats["rooms"] else 0
    recent = db.scalars(select(Booking).options(selectinload(Booking.customer), selectinload(Booking.room)).order_by(Booking.created_at.desc()).limit(6)).all()
    return templates.TemplateResponse("dashboard.html", page_context(request, user, "dashboard", stats=stats, recent=recent))


@app.get("/rooms", response_class=HTMLResponse)
def rooms_page(request: Request, user=Depends(get_current_user), db: Session = Depends(get_db)):
    rooms = db.scalars(select(Room).options(selectinload(Room.room_type)).order_by(Room.number)).all()
    room_types = db.scalars(select(RoomType).order_by(RoomType.name)).all()
    return templates.TemplateResponse("rooms.html", page_context(request, user, "rooms", rooms=rooms, room_types=room_types))


@app.get("/bookings", response_class=HTMLResponse)
def bookings_page(request: Request, user=Depends(get_current_user), db: Session = Depends(get_db)):
    bookings = db.scalars(select(Booking).options(selectinload(Booking.customer), selectinload(Booking.room).selectinload(Room.room_type)).order_by(Booking.created_at.desc())).all()
    customers = db.scalars(select(Customer).order_by(Customer.full_name)).all()
    rooms = db.scalars(select(Room).options(selectinload(Room.room_type)).order_by(Room.number)).all()
    active_services = db.scalars(select(HotelService).where(HotelService.active == True).order_by(HotelService.name)).all()
    return templates.TemplateResponse("bookings.html", page_context(request, user, "bookings", bookings=bookings, customers=customers, rooms=rooms, services=active_services))


@app.get("/customers", response_class=HTMLResponse)
def customers_page(request: Request, user=Depends(get_current_user), db: Session = Depends(get_db)):
    customers = db.scalars(select(Customer).options(selectinload(Customer.bookings)).order_by(Customer.full_name)).all()
    return templates.TemplateResponse("customers.html", page_context(request, user, "customers", customers=customers))


@app.get("/services", response_class=HTMLResponse)
def services_page(request: Request, user=Depends(get_current_user), db: Session = Depends(get_db)):
    services = db.scalars(select(HotelService).order_by(HotelService.active.desc(), HotelService.name)).all()
    return templates.TemplateResponse("services.html", page_context(request, user, "services", services=services))


@app.get("/users", response_class=HTMLResponse)
def users_page(request: Request, user=Depends(require_roles(Role.admin)), db: Session = Depends(get_db)):
    users = db.scalars(select(User).order_by(User.full_name)).all()
    return templates.TemplateResponse("users.html", page_context(request, user, "users", users=users))


@app.get("/invoices", response_class=HTMLResponse)
def invoices_page(request: Request, user=Depends(get_current_user), db: Session = Depends(get_db)):
    invoices = db.scalars(select(Invoice).options(selectinload(Invoice.booking).selectinload(Booking.customer), selectinload(Invoice.booking).selectinload(Booking.room)).order_by(Invoice.issued_at.desc())).all()
    return templates.TemplateResponse("invoices.html", page_context(request, user, "invoices", invoices=invoices))


@app.get("/ai", response_class=HTMLResponse)
def ai_page(request: Request, user=Depends(get_current_user), db: Session = Depends(get_db)):
    bookings = db.scalars(select(Booking).options(selectinload(Booking.customer), selectinload(Booking.room)).order_by(Booking.created_at.desc()).limit(50)).all()
    return templates.TemplateResponse("ai.html", page_context(request, user, "ai", bookings=bookings))


@app.get("/reports", response_class=HTMLResponse)
def reports_page(request: Request, user=Depends(get_current_user), db: Session = Depends(get_db)):
    today = date.today()
    periods = []
    for offset in range(5, -1, -1):
        year = today.year if today.month - offset > 0 else today.year - 1
        month = (today.month - offset - 1) % 12 + 1
        periods.append((year, month))
    total_rooms = db.scalar(select(func.count(Room.id))) or 0
    labels, occupancy, revenue = [], [], []
    for year, month in periods:
        start = date(year, month, 1)
        next_start = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
        month_bookings = db.scalars(select(Booking).where(Booking.status != BookingStatus.cancelled, Booking.check_in < next_start, Booking.check_out > start)).all()
        room_nights = sum((min(item.check_out, next_start) - max(item.check_in, start)).days for item in month_bookings)
        capacity = total_rooms * monthrange(year, month)[1]
        labels.append(f"T{month}/{str(year)[2:]}")
        occupancy.append(round(float(room_nights or 0) / capacity * 100, 1) if capacity else 0)
        month_revenue = db.scalar(select(func.coalesce(func.sum(Invoice.paid_amount), 0)).where(Invoice.issued_at >= datetime(year, month, 1), Invoice.issued_at < (datetime(year + 1, 1, 1) if month == 12 else datetime(year, month + 1, 1)))) or 0
        revenue.append(round(float(month_revenue) / 1_000_000, 1))
    summary = {"occupancy": occupancy[-1] if occupancy else 0, "revenue": revenue[-1] if revenue else 0, "bookings": db.scalar(select(func.count(Booking.id)).where(Booking.status != BookingStatus.cancelled)) or 0, "customers": db.scalar(select(func.count(Customer.id))) or 0}
    return templates.TemplateResponse("reports.html", page_context(request, user, "reports", labels=labels, occupancy=occupancy, revenue=revenue, summary=summary))
