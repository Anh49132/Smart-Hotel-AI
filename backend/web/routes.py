from backend.dependencies import get_current_user, require_roles
from backend.models import Role
from backend.services.auth_service import authenticate
from backend.services.page_service import ai_page_context, bookings_page_context, customers_page_context, dashboard_context, invoices_page_context, reports_page_context, rooms_page_context, services_page_context, users_page_context
from core.config import FRONTEND_DIR
from core.database import get_db
from core.security import create_token
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

router = APIRouter()
templates = Jinja2Templates(directory=FRONTEND_DIR / "templates")
STATUS_LABELS = {
    "available": "Trống", "occupied": "Đang ở", "cleaning": "Đang dọn", "maintenance": "Bảo trì",
    "confirmed": "Đã xác nhận", "checked_in": "Đang lưu trú", "checked_out": "Đã trả phòng", "cancelled": "Đã hủy",
    "unpaid": "Chưa thanh toán", "partial": "Thanh toán một phần", "paid": "Đã thanh toán",
}
templates.env.globals["status_label"] = lambda value: STATUS_LABELS.get(getattr(value, "value", value), getattr(value, "value", value))

@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request): return templates.TemplateResponse("pages/login.html", {"request": request})


@router.post("/login")
def login(request: Request, username: str = Form(), password: str = Form(), db: Session = Depends(get_db)):
    user = authenticate(db, username, password)
    if not user: return templates.TemplateResponse("pages/login.html", {"request": request, "error": "Sai tên đăng nhập hoặc mật khẩu"}, status_code=401)
    response = RedirectResponse("/", 303); response.set_cookie("access_token", create_token(user.id, user.role.value), httponly=True, samesite="lax"); return response


@router.get("/logout")
def logout():
    response = RedirectResponse("/login", 303); response.delete_cookie("access_token"); return response


def page_context(request, user, active, **extra): return {"request": request, "user": user, "active": active, **extra}


@router.get("/", response_class=HTMLResponse)
def dashboard(request: Request, user=Depends(get_current_user), db: Session = Depends(get_db)):
    return templates.TemplateResponse('pages/dashboard.html', page_context(request, user, 'dashboard', **dashboard_context(db)))


@router.get("/rooms", response_class=HTMLResponse)
def rooms_page(request: Request, user=Depends(get_current_user), db: Session = Depends(get_db)):
    return templates.TemplateResponse('pages/rooms.html', page_context(request, user, 'rooms', **rooms_page_context(db)))


@router.get("/bookings", response_class=HTMLResponse)
def bookings_page(request: Request, user=Depends(get_current_user), db: Session = Depends(get_db)):
    return templates.TemplateResponse('pages/bookings.html', page_context(request, user, 'bookings', **bookings_page_context(db)))


@router.get("/customers", response_class=HTMLResponse)
def customers_page(request: Request, user=Depends(get_current_user), db: Session = Depends(get_db)):
    return templates.TemplateResponse('pages/customers.html', page_context(request, user, 'customers', **customers_page_context(db)))


@router.get("/services", response_class=HTMLResponse)
def services_page(request: Request, user=Depends(get_current_user), db: Session = Depends(get_db)):
    return templates.TemplateResponse('pages/services.html', page_context(request, user, 'services', **services_page_context(db)))


@router.get("/users", response_class=HTMLResponse)
def users_page(request: Request, user=Depends(require_roles(Role.admin)), db: Session = Depends(get_db)):
    return templates.TemplateResponse('pages/users.html', page_context(request, user, 'users', **users_page_context(db)))


@router.get("/invoices", response_class=HTMLResponse)
def invoices_page(request: Request, user=Depends(get_current_user), db: Session = Depends(get_db)):
    return templates.TemplateResponse('pages/invoices.html', page_context(request, user, 'invoices', **invoices_page_context(db)))


@router.get("/ai", response_class=HTMLResponse)
def ai_page(request: Request, user=Depends(get_current_user), db: Session = Depends(get_db)):
    return templates.TemplateResponse('pages/ai.html', page_context(request, user, 'ai', **ai_page_context(db)))


@router.get("/reports", response_class=HTMLResponse)
def reports_page(request: Request, user=Depends(get_current_user), db: Session = Depends(get_db)):
    return templates.TemplateResponse('pages/reports.html', page_context(request, user, 'reports', **reports_page_context(db)))
