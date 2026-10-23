from backend.dependencies import get_current_user, require_roles
from backend.models import Role, RoomType, RatePlan, User, Room
from backend.services.maintenance_service import blocks
from backend.services.frontdesk_service import desk_rows
from backend.services.customers_service import customers as customer_search,customer_detail
from backend.services.folio_service import folio,receipt_document
from backend.services.housekeeping_service import list_tasks
from sqlalchemy import select
from datetime import date, timedelta
from core.hotel_time import hotel_today
from backend.services.calendar_service import room_calendar
from fastapi import Query
from backend.services.auth_service import authenticate
from backend.services.booking_detail_service import booking_detail, active_service_options
from backend.services.page_service import ai_page_context, bookings_page_context, customers_page_context, dashboard_context, invoices_page_context, reports_page_context, rooms_page_context, services_page_context, users_page_context
from core.config import FRONTEND_DIR, settings
from core.database import get_db
from core.security import set_session_cookie
from core.login_limiter import login_limiter
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

router = APIRouter()
templates = Jinja2Templates(directory=FRONTEND_DIR / "templates")
STATUS_LABELS = {
    "available": "Trống", "occupied": "Đang ở", "cleaning": "Đang dọn", "maintenance": "Bảo trì",
    "confirmed": "Đã xác nhận", "checked_in": "Đang lưu trú", "checked_out": "Đã trả phòng", "cancelled": "Đã hủy", "no_show":"Khách không đến",
    "unpaid": "Chưa thanh toán", "partial": "Thanh toán một phần", "paid": "Đã thanh toán",
}
templates.env.globals["status_label"] = lambda value: STATUS_LABELS.get(getattr(value, "value", value), getattr(value, "value", value))

@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request): return templates.TemplateResponse("pages/login.html", {"request": request,"show_demo":settings.app_env=="development" and settings.seed_demo_data})


@router.post("/login")
def login(request: Request, username: str = Form(), password: str = Form(), db: Session = Depends(get_db)):
    login_limiter.check(request.client.host if request.client else 'unknown', username)
    user = authenticate(db, username, password)
    if not user: return templates.TemplateResponse("pages/login.html", {"request": request,"show_demo":settings.app_env=="development" and settings.seed_demo_data, "error": "Sai tên đăng nhập hoặc mật khẩu"}, status_code=401)
    response = RedirectResponse('/account' if user.must_change_password else '/housekeeping' if user.role==Role.housekeeping else '/', 303)
    set_session_cookie(response, user)
    return response


@router.get("/logout")
def logout():
    response = RedirectResponse("/login", 303); response.delete_cookie("access_token"); return response


def page_context(request, user, active, **extra): return {"request": request, "user": user, "active": active, **extra}


@router.get('/account', response_class=HTMLResponse)
def account_page(request: Request, user=Depends(get_current_user)):
    return templates.TemplateResponse('pages/account.html', page_context(request, user, 'account'))


@router.get('/housekeeping', response_class=HTMLResponse)
def housekeeping_page(request:Request,user=Depends(require_roles(Role.admin,Role.receptionist,Role.housekeeping)),db:Session=Depends(get_db)):
    staff=db.scalars(select(User).where(User.role==Role.housekeeping,User.is_active.is_(True))).all() if user.role!=Role.housekeeping else []
    return templates.TemplateResponse('pages/housekeeping.html',page_context(request,user,'housekeeping',tasks=list_tasks(db,user),staff=staff))


@router.get('/maintenance',response_class=HTMLResponse)
def maintenance_page(request:Request,user=Depends(require_roles(Role.admin,Role.receptionist)),db:Session=Depends(get_db)):
    return templates.TemplateResponse('pages/maintenance.html',page_context(request,user,'maintenance',blocks=blocks(db),rooms=db.scalars(select(Room).order_by(Room.number)).all(),staff=db.scalars(select(User).where(User.role.in_((Role.admin,Role.receptionist)),User.is_active.is_(True))).all()))


@router.get('/frontdesk',response_class=HTMLResponse)
def frontdesk_page(request:Request,user=Depends(require_roles(Role.admin,Role.receptionist)),db:Session=Depends(get_db)):
    return templates.TemplateResponse('pages/frontdesk.html',page_context(request,user,'frontdesk',desk=desk_rows(db),tomorrow=str(hotel_today()+timedelta(days=1))))


@router.get("/", response_class=HTMLResponse)
def dashboard(request: Request, user=Depends(get_current_user), db: Session = Depends(get_db)):
    return templates.TemplateResponse('pages/dashboard.html', page_context(request, user, 'dashboard', **dashboard_context(db)))


@router.get("/rooms", response_class=HTMLResponse)
def rooms_page(request: Request, user=Depends(get_current_user), db: Session = Depends(get_db)):
    return templates.TemplateResponse('pages/rooms.html', page_context(request, user, 'rooms', **rooms_page_context(db)))


@router.get('/rates', response_class=HTMLResponse)
def rates_page(request: Request, user=Depends(require_roles(Role.admin)), db: Session = Depends(get_db)):
    types = db.scalars(select(RoomType).order_by(RoomType.name)).all()
    plans = db.scalars(select(RatePlan).order_by(RatePlan.start_date)).all()
    return templates.TemplateResponse('pages/rates.html', page_context(request, user, 'rates', room_types=types, plans=plans, type_names={t.id:t.name for t in types}))


@router.get('/calendar', response_class=HTMLResponse)
def calendar_page(request: Request, start: date | None = None, end: date | None = None, guests: int = Query(1,ge=1,le=20), type_id: int | None = None, floor: int | None = None, page: int = Query(1,ge=1), user=Depends(get_current_user), db: Session = Depends(get_db)):
    start=start or hotel_today()
    end=end or start+timedelta(days=14)
    calendar=room_calendar(db,start,end,guests,type_id,floor,page)
    return templates.TemplateResponse('pages/calendar.html',page_context(request,user,'calendar',calendar=calendar,types=db.scalars(select(RoomType).order_by(RoomType.name)).all(),guests=guests,type_id=type_id,floor=floor))


@router.get("/bookings", response_class=HTMLResponse)
def bookings_page(request: Request, user=Depends(get_current_user), db: Session = Depends(get_db)):
    return templates.TemplateResponse('pages/bookings.html', page_context(request, user, 'bookings', **bookings_page_context(db)))


@router.get("/customers", response_class=HTMLResponse)
def customers_page(request: Request,q:str=Query('',max_length=100),page:int=Query(1,ge=1),user=Depends(get_current_user), db: Session = Depends(get_db)):
    result=customer_search(db,q,page,user.role in (Role.admin,Role.receptionist))
    return templates.TemplateResponse('pages/customers.html', page_context(request, user, 'customers', result=result))


@router.get('/customers/{customer_id}',response_class=HTMLResponse)
def customer_detail_page(customer_id:int,request:Request,page:int=Query(1,ge=1),user=Depends(get_current_user),db:Session=Depends(get_db)):
    return templates.TemplateResponse('pages/customer_detail.html',page_context(request,user,'customers',guest=customer_detail(db,customer_id,user.role in (Role.admin,Role.receptionist),page)))


@router.get('/bookings/{booking_id}/folio',response_class=HTMLResponse)
def folio_page(booking_id:int,request:Request,user=Depends(require_roles(Role.admin,Role.accountant)),db:Session=Depends(get_db)):
    return templates.TemplateResponse('pages/folio_print.html',{'request':request,'folio':folio(db,booking_id)})


@router.get('/receipts/{entry_id}/print',response_class=HTMLResponse)
def receipt_print(entry_id:int,request:Request,user=Depends(require_roles(Role.admin,Role.accountant,Role.receptionist)),db:Session=Depends(get_db)):
    return templates.TemplateResponse('pages/receipt_print.html',{'request':request,'receipt':receipt_document(db,entry_id,user)})


@router.get('/bookings/{booking_id}', response_class=HTMLResponse)
def booking_detail_page(booking_id: int, request: Request, user=Depends(get_current_user), db: Session = Depends(get_db)):
    detail = booking_detail(db, booking_id, user.role.value)
    return templates.TemplateResponse('pages/booking_detail.html', page_context(request, user, 'bookings', detail=detail, services=active_service_options(db)))


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
