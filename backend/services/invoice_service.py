from backend.models import Booking, Invoice, PaymentStatus, ServiceUsage
from backend.schemas import PaymentIn
from decimal import Decimal
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

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


def invoice(booking_id: int, discount: Decimal, db: Session):
    booking = db.get(Booking, booking_id)
    if not booking:
        raise HTTPException(404, 'Không tìm thấy đặt phòng')
    return calculate_invoice(db, booking, discount)

def pay(invoice_id: int, data: PaymentIn, db: Session):
    item = db.get(Invoice, invoice_id)
    if not item:
        raise HTTPException(404, 'Không tìm thấy hóa đơn')
    return register_payment(db, item, data.amount)
