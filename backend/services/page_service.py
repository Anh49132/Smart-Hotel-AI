from .money_service import charge_total
from backend.models import Booking, BookingStatus, Customer, HotelService, Invoice, Room, RoomStatus, RoomType, User
from datetime import date, datetime
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

def dashboard_context(db: Session):
    stats = {'rooms': db.scalar(select(func.count(Room.id))) or 0, 'available': db.scalar(select(func.count(Room.id)).where(Room.status == RoomStatus.available)) or 0, 'today': db.scalar(select(func.count(Booking.id)).where(Booking.check_in == date.today())) or 0, 'revenue': db.scalar(select(func.coalesce(func.sum(Invoice.paid_amount), 0))) or 0}
    stats['occupancy'] = round((stats['rooms'] - stats['available']) / stats['rooms'] * 100) if stats['rooms'] else 0
    recent = db.scalars(select(Booking).options(selectinload(Booking.customer), selectinload(Booking.room)).order_by(Booking.created_at.desc()).limit(6)).all()
    return {'stats': stats, 'recent': recent}

def rooms_page_context(db: Session):
    rooms = db.scalars(select(Room).options(selectinload(Room.room_type)).order_by(Room.number)).all()
    room_types = db.scalars(select(RoomType).order_by(RoomType.name)).all()
    return {'rooms': rooms, 'room_types': room_types}

def bookings_page_context(db: Session):
    bookings = db.scalars(select(Booking).options(selectinload(Booking.customer), selectinload(Booking.room).selectinload(Room.room_type)).order_by(Booking.created_at.desc())).all()
    customers = db.scalars(select(Customer).order_by(Customer.full_name)).all()
    rooms = db.scalars(select(Room).options(selectinload(Room.room_type)).order_by(Room.number)).all()
    active_services = db.scalars(select(HotelService).where(HotelService.active == True).order_by(HotelService.name)).all()
    return {'bookings': bookings, 'customers': customers, 'rooms': rooms, 'services': active_services}

def customers_page_context(db: Session):
    customers = db.scalars(select(Customer).options(selectinload(Customer.bookings)).order_by(Customer.full_name)).all()
    return {'customers': customers}

def services_page_context(db: Session):
    services = db.scalars(select(HotelService).order_by(HotelService.active.desc(), HotelService.name)).all()
    return {'services': services}

def users_page_context(db: Session):
    users = db.scalars(select(User).order_by(User.full_name)).all()
    return {'users': users}

def invoices_page_context(db: Session):
    invoices = db.scalars(select(Invoice).options(selectinload(Invoice.booking).selectinload(Booking.customer), selectinload(Invoice.booking).selectinload(Booking.room)).order_by(Invoice.issued_at.desc())).all()
    for inv in invoices:
        inv.effective_total=charge_total(db,inv.booking)
        inv.balance_due=inv.effective_total-inv.paid_amount
        inv.adjustment_amount=inv.effective_total-inv.total
    return {'invoices': invoices}

def ai_page_context(db: Session):
    bookings = db.scalars(select(Booking).options(selectinload(Booking.customer), selectinload(Booking.room)).order_by(Booking.created_at.desc()).limit(50)).all()
    return {'bookings': bookings}
