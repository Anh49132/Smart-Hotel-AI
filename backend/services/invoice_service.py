from decimal import Decimal, ROUND_HALF_UP
from fastapi import HTTPException
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session
from backend.models import Booking, BookingStatus, Invoice, Payment, PaymentStatus, ServiceUsage, BookingSurcharge
from backend.schemas import PaymentIn
from .transactions import lock_room, write_transaction
from .rates_service import booked_room_amount
from .money_service import net_received


def money(value):
    return Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def calculate_invoice(db: Session, booking: Booking, discount: Decimal | None = None, commit: bool = True, allow_closed_booking:bool=False) -> Invoice:
    if booking.status in (BookingStatus.cancelled, BookingStatus.no_show) and not allow_closed_booking:
        raise HTTPException(409, "Không lập hóa đơn lưu trú cho đặt phòng đã hủy")
    if booking.booked_nightly_rate is None:
        raise HTTPException(409, "Đặt phòng chưa có giá đã chốt; hãy chạy migration")
    invoice = db.scalar(select(Invoice).where(Invoice.booking_id == booking.id).with_for_update().execution_options(populate_existing=True))
    nights = (booking.check_out - booking.check_in).days
    if nights <= 0:
        raise HTTPException(409, "Khoảng ngày lưu trú không hợp lệ")
    # Keep historical finalized amounts exact, even if a legacy nightly average rounded.
    finalized = invoice is not None and booking.status == BookingStatus.checked_out
    room_amount = invoice.room_amount if finalized else money(booked_room_amount(db, booking))
    service_amount = invoice.service_amount if finalized else money(db.scalar(select(func.coalesce(func.sum(ServiceUsage.unit_price * ServiceUsage.quantity), 0)).where(ServiceUsage.booking_id == booking.id)))
    if discount is not None and discount != money(discount):
        raise HTTPException(400, "Giảm giá có tối đa hai chữ số thập phân")
    discount = money(invoice.discount if discount is None and invoice else (discount or 0))
    surcharge_amount = invoice.surcharge_amount if finalized else money(db.scalar(select(func.coalesce(func.sum(BookingSurcharge.amount),0)).where(BookingSurcharge.booking_id==booking.id)))
    subtotal = room_amount + service_amount + surcharge_amount
    if discount < 0 or discount > subtotal:
        raise HTTPException(400, "Giảm giá phải từ 0 đến tổng tiền phòng và dịch vụ")
    total = money(subtotal - discount)
    if total > Decimal('9999999999.99'):
        raise HTTPException(400,'Tổng hóa đơn vượt giới hạn')
    if invoice is not None and invoice.paid_amount > total:
        raise HTTPException(400, "Tổng hóa đơn không được thấp hơn số tiền đã thanh toán")
    if invoice is None:
        paid=net_received(db,booking.id)
        if paid>total:raise HTTPException(400,'Tiền đã thu lớn hơn tổng mới; cần xử lý hoàn/điều chỉnh')
        invoice = Invoice(booking_id=booking.id, paid_amount=paid)
    invoice.surcharge_amount = surcharge_amount
    invoice.room_amount, invoice.service_amount, invoice.discount, invoice.total = room_amount, service_amount, discount, total
    invoice.payment_status = PaymentStatus.paid if invoice.paid_amount == total else (PaymentStatus.partial if invoice.paid_amount else PaymentStatus.unpaid)
    db.add(invoice)
    if commit:
        db.commit()
        db.refresh(invoice)
    return invoice


def register_payment(db: Session, invoice: Invoice, amount: Decimal, actor_id: int | None = None) -> Invoice:
    return pay(invoice.id,PaymentIn(amount=amount),db,actor_id)


def invoice(booking_id: int, discount: Decimal | None, db: Session):
    with write_transaction(db):
        room_id = db.scalar(select(Booking.room_id).where(Booking.id == booking_id))
        if room_id is None:
            raise HTTPException(404, "Không tìm thấy đặt phòng")
        lock_room(db, room_id)
        booking = db.scalar(select(Booking).where(Booking.id == booking_id).with_for_update().execution_options(populate_existing=True))
        if booking.room_id != room_id:
            raise HTTPException(409, 'Đặt phòng vừa đổi phòng, hãy tải lại và thử lại')
        return calculate_invoice(db, booking, discount)


def pay(invoice_id: int, data: PaymentIn, db: Session, actor_id: int | None = None):
    from .money_service import receipt
    from backend.schemas.inputs import ReceiptIn
    from uuid import uuid4
    booking_id=db.scalar(select(Invoice.booking_id).where(Invoice.id==invoice_id))
    if booking_id is None:raise HTTPException(404,'Không tìm thấy hóa đơn')
    payload=ReceiptIn(**{**data.model_dump(),'request_key':data.request_key or uuid4().hex,'kind':'payment'})
    receipt(db,booking_id,payload,actor_id)
    return db.get(Invoice,invoice_id)
