"""One canonical cash ledger. Payment rows are compatibility mirrors, never summed twice."""
from decimal import Decimal
from uuid import uuid4
from fastapi import HTTPException
from sqlalchemy import select,func,case
from backend.models import Booking,Invoice,MoneyEntry,Payment,PaymentStatus,ServiceUsage,BookingSurcharge,FinancialAdjustment
from .transactions import lock_room,write_transaction
from .rates_service import booked_room_amount


def lock_booking(db,booking_id):
    room_id=db.scalar(select(Booking.room_id).where(Booking.id==booking_id))
    if room_id is None:raise HTTPException(404,'Không tìm thấy đặt phòng')
    lock_room(db,room_id)
    booking=db.scalar(select(Booking).where(Booking.id==booking_id).with_for_update().execution_options(populate_existing=True))
    if booking.room_id!=room_id:raise HTTPException(409,'Phòng vừa thay đổi; hãy tải lại')
    return booking


def net_received(db,booking_id):
    return Decimal(db.scalar(select(func.coalesce(func.sum(case((MoneyEntry.kind=='refund',-MoneyEntry.amount),else_=MoneyEntry.amount)),0)).where(MoneyEntry.booking_id==booking_id)))


def charge_total(db,booking):
    invoice=db.scalar(select(Invoice).where(Invoice.booking_id==booking.id))
    if invoice:
        adjustment=db.scalar(select(func.coalesce(func.sum(FinancialAdjustment.amount),0)).where(FinancialAdjustment.booking_id==booking.id))
        return invoice.total+adjustment
    services=db.scalar(select(func.coalesce(func.sum(ServiceUsage.quantity*ServiceUsage.unit_price),0)).where(ServiceUsage.booking_id==booking.id))
    fees=db.scalar(select(func.coalesce(func.sum(BookingSurcharge.amount),0)).where(BookingSurcharge.booking_id==booking.id))
    return booked_room_amount(db,booking)+services+fees


def balance(db,booking):
    entries=db.scalars(select(MoneyEntry).where(MoneyEntry.booking_id==booking.id).order_by(MoneyEntry.id)).all()
    received=sum((e.amount for e in entries if e.kind!='refund'),Decimal(0))
    refunded=sum((e.amount for e in entries if e.kind=='refund'),Decimal(0))
    deposits=sum((e.amount for e in entries if e.kind=='deposit'),Decimal(0))
    charge=charge_total(db,booking)
    return {'charge':charge,'received':received,'refunded':refunded,'net_received':received-refunded,'deposits':deposits,'balance':charge-received+refunded}


def serialized_balance(db,booking):
    return {key:format(value,'.2f') for key,value in balance(db,booking).items()}


def receipt(db,booking_id,data,actor_id=None):
    with write_transaction(db):
        booking=lock_booking(db,booking_id)
        key=data.request_key or uuid4().hex
        existing=db.scalar(select(MoneyEntry).where(MoneyEntry.booking_id==booking_id,MoneyEntry.request_key==key))
        if existing:
            if (existing.amount,existing.method,existing.reference,existing.kind,existing.actor_id)!=(data.amount,data.method,data.reference,data.kind,actor_id):
                raise HTTPException(409,'Mã chống lặp đã dùng cho giao dịch khác')
            result={'id':existing.id,'replayed':True}
            db.rollback()
            return result
        if booking.status.value in ('cancelled','no_show') and not (data.kind=='payment' and db.scalar(select(FinancialAdjustment.id).where(FinancialAdjustment.booking_id==booking_id))):
            raise HTTPException(409,'Không thu tiền lưu trú cho lịch đã hủy/không đến')
        if data.kind=='deposit' and booking.status.value!='confirmed':
            raise HTTPException(409,'Chỉ thu cọc trước khi nhận phòng')
        invoice=db.scalar(select(Invoice).where(Invoice.booking_id==booking_id).with_for_update().execution_options(populate_existing=True))
        net=net_received(db,booking_id)
        if invoice and invoice.paid_amount!=net:
            raise HTTPException(409,'Số đã thu chưa khớp sổ giao dịch; cần đối chiếu dữ liệu cũ')
        total=charge_total(db,booking)
        if net+data.amount>total:raise HTTPException(400,'Số tiền thu vượt số dư còn phải thu')
        mirror=None
        if invoice and data.kind=='payment':
            mirror=Payment(invoice_id=invoice.id,amount=data.amount,paid_by=actor_id)
            db.add(mirror);db.flush()
        entry=MoneyEntry(booking_id=booking_id,payment_id=mirror.id if mirror else None,amount=data.amount,kind=data.kind,method=data.method,reference=data.reference,request_key=key,actor_id=actor_id)
        db.add(entry)
        if invoice:
            invoice.paid_amount=net+data.amount
            invoice.payment_status=PaymentStatus.paid if invoice.paid_amount>=total else PaymentStatus.partial
        db.commit();db.refresh(entry)
        return {'id':entry.id,'replayed':False}
