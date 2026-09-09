from datetime import date
from decimal import Decimal
from typing import Optional
from uuid import uuid4
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from .models import Booking, BookingStatus, Invoice, PaymentStatus, Room, RoomStatus, ServiceUsage
from .schemas import BookingIn


ACTIVE_BOOKING_STATUSES = (BookingStatus.confirmed, BookingStatus.checked_in)


def room_is_available(db: Session, room_id: int, check_in: date, check_out: date, exclude_id: Optional[int] = None) -> bool:
    query = select(Booking.id).where(
        Booking.room_id == room_id,
        Booking.status.in_(ACTIVE_BOOKING_STATUSES),
        Booking.check_in < check_out,
        check_in < Booking.check_out,
    )
    if exclude_id:
        query = query.where(Booking.id != exclude_id)
    return db.scalar(query.limit(1)) is None


def create_booking(db: Session, data: BookingIn) -> Booking:
    room = db.execute(select(Room).where(Room.id == data.room_id).with_for_update()).scalar_one_or_none()
    if not room or room.status == RoomStatus.maintenance:
        raise HTTPException(400, "Phòng không tồn tại hoặc đang bảo trì")
    if data.guests > room.room_type.capacity:
        raise HTTPException(400, "Số khách vượt sức chứa của phòng")
    if not room_is_available(db, data.room_id, data.check_in, data.check_out):
        raise HTTPException(409, "Phòng đã có lịch trùng trong khoảng ngày này")
    booking = Booking(code=f"BK-{uuid4().hex[:8].upper()}", **data.model_dump())
    db.add(booking)
    db.commit()
    db.refresh(booking)
    return booking


def calculate_invoice(db: Session, booking: Booking, discount: Decimal = Decimal("0")) -> Invoice:
    nights = (booking.check_out - booking.check_in).days
    room_amount = Decimal(nights) * booking.room.room_type.nightly_rate
    service_amount = db.scalar(select(func.coalesce(func.sum(ServiceUsage.unit_price * ServiceUsage.quantity), 0)).where(ServiceUsage.booking_id == booking.id))
    total = max(Decimal("0"), room_amount + Decimal(service_amount) - discount)
    invoice = booking.invoice or Invoice(booking_id=booking.id, room_amount=room_amount, service_amount=service_amount, total=total)
    invoice.room_amount, invoice.service_amount, invoice.discount, invoice.total = room_amount, service_amount, discount, total
    db.add(invoice)
    db.commit()
    db.refresh(invoice)
    return invoice


def register_payment(db: Session, invoice: Invoice, amount: Decimal) -> Invoice:
    if invoice.paid_amount + amount > invoice.total:
        raise HTTPException(400, "Số tiền thanh toán vượt tổng hóa đơn")
    invoice.paid_amount += amount
    invoice.payment_status = PaymentStatus.paid if invoice.paid_amount == invoice.total else PaymentStatus.partial
    db.commit()
    db.refresh(invoice)
    return invoice
