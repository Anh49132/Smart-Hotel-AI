from backend.models import Booking, Invoice, Payment, PaymentStatus, ServiceUsage
from backend.schemas import PaymentIn
from decimal import Decimal
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

def calculate_invoice(db: Session, booking: Booking, discount: Decimal = Decimal("0"), commit: bool = True) -> Invoice:
    if discount < 0:
        raise HTTPException(400, "Giảm giá không được âm")
    nights = (booking.check_out - booking.check_in).days
    room_amount = Decimal(nights) * booking.room.room_type.nightly_rate
    service_amount = db.scalar(select(func.coalesce(func.sum(ServiceUsage.unit_price * ServiceUsage.quantity), 0)).where(ServiceUsage.booking_id == booking.id))
    total = max(Decimal("0"), room_amount + Decimal(service_amount) - discount)
    invoice = booking.invoice or Invoice(booking_id=booking.id, room_amount=room_amount, service_amount=service_amount, total=total)
    if invoice.paid_amount and total < invoice.paid_amount:
        raise HTTPException(400, "Tổng hóa đơn không được thấp hơn số tiền đã thanh toán")
    invoice.room_amount, invoice.service_amount, invoice.discount, invoice.total = room_amount, service_amount, discount, total
    if invoice.paid_amount:
        invoice.payment_status = PaymentStatus.paid if invoice.paid_amount == total else PaymentStatus.partial
    db.add(invoice)
    if commit:
        db.commit()
        db.refresh(invoice)
    return invoice

def register_payment(db: Session, invoice: Invoice, amount: Decimal, actor_id: int | None = None) -> Invoice:
    if amount <= 0:
        raise HTTPException(400, "Số tiền thanh toán phải lớn hơn 0")
    if invoice.paid_amount + amount > invoice.total:
        raise HTTPException(400, "Số tiền thanh toán vượt tổng hóa đơn")
    invoice.paid_amount += amount
    invoice.payment_status = PaymentStatus.paid if invoice.paid_amount == invoice.total else PaymentStatus.partial
    db.add(Payment(invoice_id=invoice.id, amount=amount, paid_by=actor_id))
    db.commit()
    db.refresh(invoice)
    return invoice


def invoice(booking_id: int, discount: Decimal, db: Session):
    booking = db.get(Booking, booking_id)
    if not booking:
        raise HTTPException(404, 'Không tìm thấy đặt phòng')
    return calculate_invoice(db, booking, discount)

def pay(invoice_id: int, data: PaymentIn, db: Session, actor_id: int | None = None):
    item = db.execute(select(Invoice).where(Invoice.id == invoice_id).with_for_update()).scalar_one_or_none()
    if not item:
        raise HTTPException(404, 'Không tìm thấy hóa đơn')
    return register_payment(db, item, data.amount, actor_id)
