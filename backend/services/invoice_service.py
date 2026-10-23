from decimal import Decimal, ROUND_HALF_UP
from fastapi import HTTPException
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session
from backend.models import Booking, BookingStatus, Invoice, Payment, PaymentStatus, ServiceUsage
from backend.schemas import PaymentIn
from .transactions import lock_room, write_transaction


def money(value):
    return Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def calculate_invoice(db: Session, booking: Booking, discount: Decimal | None = None, commit: bool = True) -> Invoice:
    if booking.status == BookingStatus.cancelled:
        raise HTTPException(409, "Không lập hóa đơn lưu trú cho đặt phòng đã hủy")
    if booking.booked_nightly_rate is None:
        raise HTTPException(409, "Đặt phòng chưa có giá đã chốt; hãy chạy migration")
    invoice = db.scalar(select(Invoice).where(Invoice.booking_id == booking.id).with_for_update().execution_options(populate_existing=True))
    nights = (booking.check_out - booking.check_in).days
    if nights <= 0:
        raise HTTPException(409, "Khoảng ngày lưu trú không hợp lệ")
    # Keep historical finalized amounts exact, even if a legacy nightly average rounded.
    finalized = invoice is not None and booking.status == BookingStatus.checked_out
    room_amount = invoice.room_amount if finalized else money(nights * booking.booked_nightly_rate)
    service_amount = invoice.service_amount if finalized else money(db.scalar(select(func.coalesce(func.sum(ServiceUsage.unit_price * ServiceUsage.quantity), 0)).where(ServiceUsage.booking_id == booking.id)))
    if discount is not None and discount != money(discount):
        raise HTTPException(400, "Giảm giá có tối đa hai chữ số thập phân")
    discount = money(invoice.discount if discount is None and invoice else (discount or 0))
    subtotal = room_amount + service_amount
    if discount < 0 or discount > subtotal:
        raise HTTPException(400, "Giảm giá phải từ 0 đến tổng tiền phòng và dịch vụ")
    total = money(subtotal - discount)
    if invoice is not None and invoice.paid_amount > total:
        raise HTTPException(400, "Tổng hóa đơn không được thấp hơn số tiền đã thanh toán")
    if invoice is None:
        invoice = Invoice(booking_id=booking.id, paid_amount=Decimal(0))
    invoice.room_amount, invoice.service_amount, invoice.discount, invoice.total = room_amount, service_amount, discount, total
    invoice.payment_status = PaymentStatus.paid if invoice.paid_amount == total else (PaymentStatus.partial if invoice.paid_amount else PaymentStatus.unpaid)
    db.add(invoice)
    if commit:
        db.commit()
        db.refresh(invoice)
    return invoice


def register_payment(db: Session, invoice: Invoice, amount: Decimal, actor_id: int | None = None) -> Invoice:
    if amount <= 0 or amount != money(amount):
        raise HTTPException(400, "Số tiền phải lớn hơn 0 và có tối đa hai chữ số thập phân")
    if invoice.booking.status == BookingStatus.cancelled:
        raise HTTPException(409, "Không thu tiền lưu trú cho đặt phòng đã hủy")
    if invoice.paid_amount + amount > invoice.total:
        raise HTTPException(400, "Số tiền thanh toán vượt tổng hóa đơn")
    invoice.paid_amount += amount
    invoice.payment_status = PaymentStatus.paid if invoice.paid_amount == invoice.total else PaymentStatus.partial
    db.add(Payment(invoice_id=invoice.id, amount=amount, paid_by=actor_id))
    db.commit()
    db.refresh(invoice)
    return invoice


def invoice(booking_id: int, discount: Decimal | None, db: Session):
    with write_transaction(db):
        room_id = db.scalar(select(Booking.room_id).where(Booking.id == booking_id))
        if room_id is None:
            raise HTTPException(404, "Không tìm thấy đặt phòng")
        lock_room(db, room_id)
        booking = db.scalar(select(Booking).where(Booking.id == booking_id).with_for_update().execution_options(populate_existing=True))
        return calculate_invoice(db, booking, discount)


def pay(invoice_id: int, data: PaymentIn, db: Session, actor_id: int | None = None):
    with write_transaction(db):
        if db.get_bind().dialect.name == "sqlite":
            db.execute(update(Invoice).where(Invoice.id == invoice_id).values(id=Invoice.id).execution_options(synchronize_session=False))
        item = db.scalar(select(Invoice).where(Invoice.id == invoice_id).with_for_update().execution_options(populate_existing=True))
        if not item:
            raise HTTPException(404, "Không tìm thấy hóa đơn")
        return register_payment(db, item, data.amount, actor_id)
