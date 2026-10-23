from .money_service import charge_total
from backend.models import Booking, BookingStatus, Customer, HotelService, Invoice, Room, RoomStatus, RoomType, User,MoneyEntry
from datetime import date, datetime
from sqlalchemy import func, select,or_,case
from urllib.parse import urlencode
from core.hotel_time import hotel_today
from sqlalchemy.orm import Session, selectinload

def dashboard_context(db: Session):
    stats = {'rooms': db.scalar(select(func.count(Room.id))) or 0, 'available': db.scalar(select(func.count(Room.id)).where(Room.status == RoomStatus.available)) or 0, 'today': db.scalar(select(func.count(Booking.id)).where(Booking.check_in == hotel_today(),Booking.status==BookingStatus.confirmed)) or 0, 'revenue': db.scalar(select(func.coalesce(func.sum(case((MoneyEntry.kind=='refund',-MoneyEntry.amount),else_=MoneyEntry.amount)), 0))) or 0}
    stats['occupancy'] = round((stats['rooms'] - stats['available']) / stats['rooms'] * 100) if stats['rooms'] else 0
    recent = db.scalars(select(Booking).options(selectinload(Booking.customer), selectinload(Booking.room)).order_by(Booking.created_at.desc(),Booking.id.desc()).limit(6)).all()
    return {'stats': stats, 'recent': recent}

def rooms_page_context(db: Session):
    rooms = db.scalars(select(Room).options(selectinload(Room.room_type)).order_by(Room.number)).all()
    room_types = db.scalars(select(RoomType).order_by(RoomType.name)).all()
    return {'rooms': rooms, 'room_types': room_types}

def pagination(total,page,**filters):
    pages=max(1,(total+19)//20);page=min(page,pages)
    return {'total':total,'page':page,'pages':pages,'q':filters.get('q',''),'status':filters.get('status',''),'previous':'?'+urlencode(dict(filters,page=page-1)) if page>1 else None,'next':'?'+urlencode(dict(filters,page=page+1)) if page<pages else None}

def bookings_page_context(db:Session,q='',status='',page=1):
    query=select(Booking).join(Customer)
    if q:query=query.where(or_(Booking.code.contains(q,autoescape=True),Customer.full_name.contains(q,autoescape=True)))
    if status:query=query.where(Booking.status==status)
    total=db.scalar(select(func.count()).select_from(query.subquery()));pager=pagination(total,page,q=q,status=status)
    bookings=db.scalars(query.options(selectinload(Booking.customer),selectinload(Booking.room).selectinload(Room.room_type)).order_by(Booking.created_at.desc(),Booking.id.desc()).offset((pager['page']-1)*20).limit(20)).all()
    customers = db.scalars(select(Customer).order_by(Customer.full_name)).all()
    rooms = db.scalars(select(Room).options(selectinload(Room.room_type)).order_by(Room.number)).all()
    active_services = db.scalars(select(HotelService).where(HotelService.active == True).order_by(HotelService.name)).all()
    return {'bookings':bookings,'customers':customers,'rooms':rooms,'services':active_services,'pagination':pager}

def customers_page_context(db: Session):
    customers = db.scalars(select(Customer).options(selectinload(Customer.bookings)).order_by(Customer.full_name)).all()
    return {'customers': customers}

def services_page_context(db: Session):
    services = db.scalars(select(HotelService).order_by(HotelService.active.desc(), HotelService.name)).all()
    return {'services': services}

def users_page_context(db: Session):
    users = db.scalars(select(User).order_by(User.full_name)).all()
    return {'users': users}

def invoices_page_context(db:Session,q='',status='',page=1):
    query=select(Invoice).join(Booking).join(Customer)
    if q:query=query.where(or_(Booking.code.contains(q,autoescape=True),Customer.full_name.contains(q,autoescape=True)))
    if status:query=query.where(Invoice.payment_status==status)
    total=db.scalar(select(func.count()).select_from(query.subquery()));pager=pagination(total,page,q=q,status=status)
    invoices=db.scalars(query.options(selectinload(Invoice.booking).selectinload(Booking.customer),selectinload(Invoice.booking).selectinload(Booking.room)).order_by(Invoice.issued_at.desc(),Invoice.id.desc()).offset((pager['page']-1)*20).limit(20)).all()
    for inv in invoices:
        inv.effective_total=charge_total(db,inv.booking)
        inv.balance_due=inv.effective_total-inv.paid_amount
        inv.adjustment_amount=inv.effective_total-inv.total
    return {'invoices':invoices,'pagination':pager}

def ai_page_context(db: Session):
    bookings = db.scalars(select(Booking).options(selectinload(Booking.customer), selectinload(Booking.room)).order_by(Booking.created_at.desc()).limit(50)).all()
    return {'bookings': bookings}
