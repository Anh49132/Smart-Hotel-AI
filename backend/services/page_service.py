from backend.models import Booking, BookingStatus, Customer, HotelService, Invoice, Room, RoomStatus, RoomType, User
from calendar import monthrange
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
    return {'invoices': invoices}

def ai_page_context(db: Session):
    bookings = db.scalars(select(Booking).options(selectinload(Booking.customer), selectinload(Booking.room)).order_by(Booking.created_at.desc()).limit(50)).all()
    return {'bookings': bookings}

def reports_page_context(db: Session):
    today = date.today()
    periods = []
    for offset in range(5, -1, -1):
        year = today.year if today.month - offset > 0 else today.year - 1
        month = (today.month - offset - 1) % 12 + 1
        periods.append((year, month))
    total_rooms = db.scalar(select(func.count(Room.id))) or 0
    labels, occupancy, revenue = ([], [], [])
    for year, month in periods:
        start = date(year, month, 1)
        next_start = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
        month_bookings = db.scalars(select(Booking).where(Booking.status != BookingStatus.cancelled, Booking.check_in < next_start, Booking.check_out > start)).all()
        room_nights = sum(((min(item.check_out, next_start) - max(item.check_in, start)).days for item in month_bookings))
        capacity = total_rooms * monthrange(year, month)[1]
        labels.append(f'T{month}/{str(year)[2:]}')
        occupancy.append(round(float(room_nights or 0) / capacity * 100, 1) if capacity else 0)
        month_revenue = db.scalar(select(func.coalesce(func.sum(Invoice.paid_amount), 0)).where(Invoice.issued_at >= datetime(year, month, 1), Invoice.issued_at < (datetime(year + 1, 1, 1) if month == 12 else datetime(year, month + 1, 1)))) or 0
        revenue.append(round(float(month_revenue) / 1000000, 1))
    summary = {'occupancy': occupancy[-1] if occupancy else 0, 'revenue': revenue[-1] if revenue else 0, 'bookings': db.scalar(select(func.count(Booking.id)).where(Booking.status != BookingStatus.cancelled)) or 0, 'customers': db.scalar(select(func.count(Customer.id))) or 0}
    return {'labels': labels, 'occupancy': occupancy, 'revenue': revenue, 'summary': summary}
