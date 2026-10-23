from datetime import datetime,time,timezone
from decimal import Decimal
from sqlalchemy import select,func,update
from fastapi import HTTPException
from backend.models import Booking,BookingStatus,BookingStatusHistory,BookingSurcharge,HotelPolicy,ServiceUsage
from core.hotel_time import hotel_now,HOTEL_TIMEZONE
from .transactions import lock_room,write_transaction
from .rates_service import booked_room_amount
from .invoice_service import calculate_invoice

DEFAULT_POLICY={'check_in_hour':14,'check_out_hour':12,'no_show_hour':23,'early_fee':Decimal(0),'late_fee':Decimal(0)}


def policy(db):
    item=db.get(HotelPolicy,1)
    return {key:getattr(item,key) for key in DEFAULT_POLICY} if item else DEFAULT_POLICY.copy()


def save_policy(db,data):
    with write_transaction(db):
        if db.get_bind().dialect.name=='sqlite':db.execute(update(HotelPolicy).where(HotelPolicy.id==1).values(id=1))
        item=db.scalar(select(HotelPolicy).where(HotelPolicy.id==1).with_for_update().execution_options(populate_existing=True))
        if not item:item=HotelPolicy(id=1);db.add(item)
        for k,v in data.model_dump().items():setattr(item,k,v)
        db.commit()
    return {'ok':True}


def threshold(day,hour):
    return datetime.combine(day,time(hour=hour),tzinfo=HOTEL_TIMEZONE)


def desk_rows(db):
    now=hotel_now();today=now.date();p=policy(db)
    bookings=db.scalars(select(Booking).where(Booking.status.in_((BookingStatus.confirmed,BookingStatus.checked_in))).order_by(Booking.check_in,Booking.id).limit(200)).all()
    result=[]
    for b in bookings:
        if b.status==BookingStatus.confirmed and b.check_in>today:continue
        inv=b.invoice
        service=db.scalar(select(func.coalesce(func.sum(ServiceUsage.unit_price*ServiceUsage.quantity),0)).where(ServiceUsage.booking_id==b.id))
        fees=db.scalar(select(func.coalesce(func.sum(BookingSurcharge.amount),0)).where(BookingSurcharge.booking_id==b.id))
        due=inv.total-inv.paid_amount if inv else booked_room_amount(db,b)+service+fees
        charged=set(db.scalars(select(BookingSurcharge.kind).where(BookingSurcharge.booking_id==b.id)).all())
        result.append({'id':b.id,'code':b.code,'customer':b.customer.full_name,'room':b.room.number,'check_in':str(b.check_in),'check_out':str(b.check_out),'status':b.status.value,
            'due':str(due),'overdue':b.status==BookingStatus.checked_in and now>threshold(b.check_out,p['check_out_hour']),
            'can_no_show':b.status==BookingStatus.confirmed and now>=threshold(b.check_in,p['no_show_hour']) and inv is None,
            'early':'early' not in charged and b.status==BookingStatus.confirmed and today==b.check_in and now<threshold(b.check_in,p['check_in_hour']),
            'late':'late' not in charged and b.status==BookingStatus.checked_in and now>threshold(b.check_out,p['check_out_hour'])})
    return {'now':now.isoformat(),'today':str(today),'policy':p,'rows':result,'limited':len(bookings)==200}


def mark_no_show(db,booking_id,actor):
    with write_transaction(db):
        room_id=db.scalar(select(Booking.room_id).where(Booking.id==booking_id))
        if room_id is None:raise HTTPException(404,'Không tìm thấy đặt phòng')
        lock_room(db,room_id)
        b=db.scalar(select(Booking).where(Booking.id==booking_id).with_for_update().execution_options(populate_existing=True))
        if b.room_id!=room_id or b.status!=BookingStatus.confirmed or hotel_now()<threshold(b.check_in,policy(db)['no_show_hour']):
            raise HTTPException(409,'Chưa đến hạn no-show hoặc trạng thái đã thay đổi')
        if b.invoice is not None:raise HTTPException(409,'Xử lý hóa đơn/tiền đã thu trước khi xác nhận no-show')
        db.add(BookingStatusHistory(booking_id=b.id,from_status=b.status,to_status=BookingStatus.no_show,changed_by=actor.id))
        b.status=BookingStatus.no_show
        db.commit()
    return {'ok':True}


def confirm_fee(db,booking_id,data,user):
    with write_transaction(db):
        room_id=db.scalar(select(Booking.room_id).where(Booking.id==booking_id))
        if room_id is None:raise HTTPException(404,'Không tìm thấy đặt phòng')
        lock_room(db,room_id)
        b=db.scalar(select(Booking).where(Booking.id==booking_id).with_for_update().execution_options(populate_existing=True))
        if b.room_id!=room_id:raise HTTPException(409,'Đặt phòng vừa đổi phòng, cần tải lại')
        now=hotel_now();p=policy(db)
        valid=(data.kind=='early' and b.status==BookingStatus.confirmed and now.date()==b.check_in and now<threshold(b.check_in,p['check_in_hour'])) or (data.kind=='late' and b.status==BookingStatus.checked_in and now>threshold(b.check_out,p['check_out_hour']))
        amount=p['early_fee' if data.kind=='early' else 'late_fee']
        if not valid or amount<=0 or amount!=data.expected_amount:raise HTTPException(409,'Chưa đủ điều kiện hoặc mức phụ thu đã đổi; cần kiểm tra lại')
        db.add(BookingSurcharge(booking_id=b.id,kind=data.kind,amount=amount,confirmed_by=user.id));db.flush()
        if b.invoice is not None:calculate_invoice(db,b,commit=False)
        db.commit()
    return {'ok':True}
