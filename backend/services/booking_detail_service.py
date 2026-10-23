"""Read-only reservation detail; opening a page never creates an invoice."""
from decimal import Decimal
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from backend.models import Booking, BookingNight, HotelService, Invoice, ServiceUsage, User, RoomStay, Room, BookingChange
from .rates_service import booked_room_amount


def amount(value):
    return format(Decimal(value), '.2f')


def booking_detail(db, booking_id, role):
    booking = db.scalar(select(Booking).where(Booking.id == booking_id).options(
        selectinload(Booking.customer), selectinload(Booking.room),
        selectinload(Booking.status_history), selectinload(Booking.service_usages).selectinload(ServiceUsage.service),
        selectinload(Booking.invoice).selectinload(Invoice.payments)))
    if not booking:
        raise HTTPException(404, 'Không tìm thấy đặt phòng')
    invoice = booking.invoice
    # Preserve finalized historical amounts even when a legacy nightly average rounded.
    room_total = invoice.room_amount if invoice and booking.status.value == 'checked_out' else booked_room_amount(db, booking)
    service_total = sum((s.unit_price * s.quantity for s in booking.service_usages), Decimal(0))
    discount = invoice.discount if invoice else Decimal(0)
    estimated = room_total + service_total - discount
    nights = db.scalars(select(BookingNight).where(BookingNight.booking_id == booking_id).order_by(BookingNight.stay_date)).all()
    changes = db.scalars(select(BookingChange).where(BookingChange.booking_id == booking_id).order_by(BookingChange.id)).all()
    actors = {c.changed_by for c in changes if c.changed_by}
    actors.update(h.changed_by for h in booking.status_history if h.changed_by)
    if invoice:
        actors.update(p.paid_by for p in invoice.payments if p.paid_by)
    names = dict(db.execute(select(User.id, User.full_name).where(User.id.in_(actors))).all()) if actors else {}
    history = [{'id':h.id, 'from_status':h.from_status.value if h.from_status else None, 'to_status':h.to_status.value,
                'at':h.changed_at.isoformat(), 'actor':names.get(h.changed_by, 'Hệ thống / chưa ghi người thao tác')} for h in booking.status_history]
    payments = [{'id':p.id, 'amount':amount(p.amount), 'at':p.paid_at.isoformat(), 'actor':names.get(p.paid_by, 'Chưa ghi người thu')} for p in invoice.payments] if invoice else []
    # Show unmatched legacy paid amounts explicitly instead of inventing transactions.
    ledger_gap = invoice.paid_amount - sum((p.amount for p in invoice.payments), Decimal(0)) if invoice else Decimal(0)
    frontdesk = role in ('admin', 'receptionist')
    finance = role in ('admin', 'accountant')
    if not finance:
        payments = []
    can_check_in = frontdesk and booking.status.value == 'confirmed' and booking.room.status.value == 'available'
    return {
        'id':booking.id, 'code':booking.code, 'status':booking.status.value, 'created_at':booking.created_at.isoformat(),
        'check_in':booking.check_in.isoformat(), 'check_out':booking.check_out.isoformat(), 'guests':booking.guests,
        'nights_count':(booking.check_out-booking.check_in).days, 'note':booking.note,
        'customer':{'name':booking.customer.full_name, 'phone':booking.customer.phone, 'email':booking.customer.email},
        'room':{'number':booking.room.number, 'type':booking.room.room_type.name, 'status':booking.room.status.value},
        'nightly_prices':[{'date':n.stay_date.isoformat(), 'amount':amount(n.amount), 'source':n.source} for n in nights],
        'rate_source':booking.booked_rate_source, 'booked_average':amount(booking.booked_nightly_rate),
        'services':[{'name':s.service.name, 'quantity':s.quantity, 'unit':s.service.unit, 'unit_price':amount(s.unit_price), 'total':amount(s.unit_price*s.quantity), 'at':s.used_at.isoformat()} for s in booking.service_usages],
        'estimate':{'room_amount':amount(room_total), 'service_amount':amount(service_total), 'discount':amount(discount), 'total':amount(estimated)},
        'invoice':{'id':invoice.id, 'room_amount':amount(invoice.room_amount), 'service_amount':amount(invoice.service_amount), 'discount':amount(invoice.discount),
                   'total':amount(invoice.total), 'paid_amount':amount(invoice.paid_amount), 'remaining':amount(invoice.total-invoice.paid_amount), 'status':invoice.payment_status.value,
                   'finalized':booking.status.value == 'checked_out', 'ledger_gap':amount(ledger_gap)} if invoice else None,
        'stays':[{'room':number,'check_in':str(stay.check_in),'check_out':str(stay.check_out)} for stay,number in db.execute(select(RoomStay,Room.number).join(Room,Room.id==RoomStay.room_id).where(RoomStay.booking_id==booking_id).order_by(RoomStay.check_in))],
        'changes':[{'reason':c.reason,'at':c.changed_at.isoformat(),'actor':names.get(c.changed_by,'Hệ thống'),'before':c.before_data,'after':c.after_data} for c in changes],
        'can_change':frontdesk and booking.status.value in ('confirmed','checked_in'),
        'history':history, 'payments':payments, 'can_view_payments':finance,
        'actions':{'check_in':can_check_in, 'cancel':frontdesk and booking.status.value == 'confirmed' and invoice is None,
                   'check_out':frontdesk and booking.status.value == 'checked_in', 'add_service':frontdesk and booking.status.value == 'checked_in',
                   'calculate':finance and booking.status.value not in ('cancelled','checked_out'),
                   'pay':finance and invoice is not None and invoice.paid_amount < invoice.total and booking.status.value != 'cancelled'},
    }


def active_service_options(db):
    return [{'id':s.id,'name':s.name,'price':amount(s.price),'unit':s.unit} for s in db.scalars(select(HotelService).where(HotelService.active.is_(True)).order_by(HotelService.name))]
