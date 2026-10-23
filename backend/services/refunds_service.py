from decimal import Decimal,ROUND_HALF_UP
from datetime import datetime
from fastapi import HTTPException
from sqlalchemy import select,update
from backend.models import Invoice,MoneyEntry,FinancialAdjustment,HotelPolicy,BookingStatus,BookingStatusHistory,PaymentStatus
from core.hotel_time import hotel_now
from .frontdesk_service import policy,threshold
from .money_service import lock_booking,net_received,charge_total
from .invoice_service import calculate_invoice
from .transactions import write_transaction


def cancellation_policy(db):
    p=db.get(HotelPolicy,1)
    return {'cancellation_percent':p.cancellation_percent if p else Decimal(0),'no_show_percent':p.no_show_percent if p else Decimal(0)}


def save_cancellation_policy(db,data):
    with write_transaction(db):
        if db.get_bind().dialect.name=='sqlite':db.execute(update(HotelPolicy).where(HotelPolicy.id==1).values(id=1))
        item=db.scalar(select(HotelPolicy).where(HotelPolicy.id==1).with_for_update().execution_options(populate_existing=True))
        if not item:item=HotelPolicy(id=1);db.add(item)
        for key,value in data.model_dump().items():setattr(item,key,value)
        db.commit()
    return {'ok':True}



def settle_cancellation(db,booking_id,data,user,preview=False):
    with write_transaction(db):
        b=lock_booking(db,booking_id)
        prior=db.scalar(select(FinancialAdjustment).where(FinancialAdjustment.booking_id==booking_id))
        if prior:
            if (prior.request_key,prior.reason,prior.target_status,prior.actor_id)!=(data.request_key,data.reason,data.target_status,user.id):raise HTTPException(409,'Lịch đã được quyết toán hủy/no-show')
            if data.expected_fee is not None and data.expected_fee!=prior.fee_amount:raise HTTPException(409,'Mã quyết toán có mức phí khác')
            result={'id':prior.id,'replayed':True,'fee_amount':str(prior.fee_amount)}
            db.rollback();return result
        if b.status not in (BookingStatus.confirmed,BookingStatus.no_show):raise HTTPException(409,'Chỉ quyết toán lịch chưa nhận phòng/không đến')
        if b.status==BookingStatus.no_show and data.target_status!='no_show':raise HTTPException(409,'Giữ nguyên trạng thái no-show đã ghi')
        if data.target_status=='no_show' and hotel_now()<threshold(b.check_in,policy(db)['no_show_hour']):raise HTTPException(409,'Chưa đến hạn no-show')
        inv=calculate_invoice(db,b,commit=False,allow_closed_booking=True)
        p=cancellation_policy(db)
        percent=p['no_show_percent' if data.target_status=='no_show' else 'cancellation_percent']
        fee=(inv.total*percent/100).quantize(Decimal('.01'),rounding=ROUND_HALF_UP)
        result={'original_total':str(inv.total),'percent':str(percent),'fee_amount':str(fee),'refundable':str(max(Decimal(0),net_received(db,b.id)-fee))}
        if preview:db.rollback();return result
        if data.expected_fee is None or data.expected_fee!=fee:raise HTTPException(409,'Cần xem và xác nhận lại phí hủy/no-show')
        entry=FinancialAdjustment(booking_id=b.id,target_status=data.target_status,original_total=inv.total,fee_amount=fee,percent=percent,amount=fee-inv.total,reason=data.reason,request_key=data.request_key,actor_id=user.id)
        db.add(entry)
        target=BookingStatus(data.target_status)
        if b.status!=target:db.add(BookingStatusHistory(booking_id=b.id,from_status=b.status,to_status=target,changed_by=user.id))
        b.status=target
        inv.payment_status=PaymentStatus.paid if inv.paid_amount>=fee else (PaymentStatus.partial if inv.paid_amount else PaymentStatus.unpaid)
        db.commit();db.refresh(entry)
        return dict(result,id=entry.id,replayed=False)


def refund(db,booking_id,data,user):
    with write_transaction(db):
        b=lock_booking(db,booking_id)
        prior=db.scalar(select(MoneyEntry).where(MoneyEntry.booking_id==booking_id,MoneyEntry.request_key==data.request_key))
        if prior:
            if (prior.kind,prior.amount,prior.method,prior.reference,prior.reason,prior.actor_id)!=('refund',data.amount,data.method,data.reference,data.reason,user.id):raise HTTPException(409,'Mã chống lặp đã dùng cho giao dịch khác')
            result={'id':prior.id,'replayed':True};db.rollback();return result
        net=net_received(db,booking_id)
        inv=db.scalar(select(Invoice).where(Invoice.booking_id==booking_id).with_for_update().execution_options(populate_existing=True))
        if inv and inv.paid_amount!=net:raise HTTPException(409,'Cần đối chiếu số đã thu trước khi hoàn')
        maximum=max(Decimal(0),net-charge_total(db,b)) if b.status in (BookingStatus.cancelled,BookingStatus.no_show) else net
        if data.amount>maximum:raise HTTPException(400,'Số hoàn vượt tiền có thể hoàn sau phí đã giữ lại')
        entry=MoneyEntry(booking_id=booking_id,kind='refund',amount=data.amount,method=data.method,reference=data.reference,reason=data.reason,request_key=data.request_key,actor_id=user.id)
        db.add(entry)
        if inv:
            inv.paid_amount=net-data.amount
            inv.payment_status=PaymentStatus.paid if inv.paid_amount>=charge_total(db,b) else (PaymentStatus.partial if inv.paid_amount else PaymentStatus.unpaid)
        db.commit();db.refresh(entry)
        return {'id':entry.id,'replayed':False}
