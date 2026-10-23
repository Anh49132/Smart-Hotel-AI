"""Read-only itemized internal documents, separate charges from money received."""
from decimal import Decimal
from sqlalchemy import select
from fastapi import HTTPException
from backend.models import Booking,BookingNight,ServiceUsage,BookingSurcharge,MoneyEntry,RoomStay,Room,User
from .rates_service import booked_room_amount


def text_amount(value):return format(Decimal(value),'.2f')


def folio(db,booking_id):
    b=db.get(Booking,booking_id)
    if not b:raise HTTPException(404,'Không tìm thấy đặt phòng')
    invoice=b.invoice
    nights=db.scalars(select(BookingNight).where(BookingNight.booking_id==booking_id).order_by(BookingNight.stay_date)).all()
    stays=db.execute(select(RoomStay,Room.number).join(Room,Room.id==RoomStay.room_id).where(RoomStay.booking_id==booking_id)).all()
    lines=[]
    if nights:
        for n in nights:
            room=next((number for s,number in stays if s.check_in<=n.stay_date<s.check_out),b.room.number)
            lines.append({'category':'room','description':f'{n.stay_date} · Phòng {room} · {n.source}','amount':n.amount})
    else:
        lines.append({'category':'room','description':'Tiền phòng legacy (không có giá chi tiết từng đêm)','amount':invoice.room_amount if invoice else booked_room_amount(db,b)})
    for usage in db.scalars(select(ServiceUsage).where(ServiceUsage.booking_id==booking_id).order_by(ServiceUsage.id)):
        lines.append({'category':'service','description':f'{usage.service.name} · {usage.quantity} {usage.service.unit} × {text_amount(usage.unit_price)}','amount':usage.unit_price*usage.quantity})
    for fee in db.scalars(select(BookingSurcharge).where(BookingSurcharge.booking_id==booking_id).order_by(BookingSurcharge.id)):
        lines.append({'category':'surcharge','description':'Phụ thu nhận sớm' if fee.kind=='early' else 'Phụ thu trả muộn','amount':fee.amount})
    if invoice:
        for category,expected in [('room',invoice.room_amount),('service',invoice.service_amount),('surcharge',invoice.surcharge_amount)]:
            actual=sum((x['amount'] for x in lines if x['category']==category),Decimal(0))
            if expected!=actual:lines.append({'category':'reconciliation','description':f'Đối chiếu {category} với hóa đơn đã lập (legacy/chưa cập nhật)','amount':expected-actual})
        if invoice.discount:lines.append({'category':'discount','description':'Giảm giá trên hóa đơn','amount':-invoice.discount})
    entries=db.scalars(select(MoneyEntry).where(MoneyEntry.booking_id==booking_id).order_by(MoneyEntry.occurred_at,MoneyEntry.id)).all()
    ids={e.actor_id for e in entries if e.actor_id}
    actors=dict(db.execute(select(User.id,User.full_name).where(User.id.in_(ids))).all()) if ids else {}
    received=sum((e.amount for e in entries if e.kind!='refund'),Decimal(0))
    refunded=sum((e.amount for e in entries if e.kind=='refund'),Decimal(0))
    charge=sum((line['amount'] for line in lines),Decimal(0))
    return {'booking_id':b.id,'code':b.code,'customer_name':b.customer.full_name,'status':b.status.value,
            'invoice_id':invoice.id if invoice else None,'finalized':bool(invoice and b.status.value=='checked_out'),
            'lines':[dict(x,amount=text_amount(x['amount'])) for x in lines],
            'transactions':[{'id':e.id,'kind':e.kind,'amount':text_amount(e.amount),'method':e.method,'reference':e.reference,'actor':actors.get(e.actor_id,'Chưa ghi người thu'),'at':e.occurred_at.isoformat()} for e in entries],
            'total':text_amount(charge),'received':text_amount(received),'refunded':text_amount(refunded),'net_received':text_amount(received-refunded),'balance':text_amount(charge-received+refunded),
            'legacy_gap':text_amount(invoice.paid_amount-received+refunded) if invoice else '0.00'}


def receipt_document(db,entry_id,user):
    entry=db.get(MoneyEntry,entry_id)
    if not entry:raise HTTPException(404,'Không tìm thấy phiếu thu')
    if user.role.value not in ('admin','accountant') and not (entry.actor_id==user.id and entry.kind=='deposit'):
        raise HTTPException(403,'Chỉ xem phiếu thu cọc do bạn ghi nhận')
    b=db.get(Booking,entry.booking_id)
    return {'id':entry.id,'booking_id':b.id,'code':b.code,'customer_name':b.customer.full_name,'kind':entry.kind,'amount':text_amount(entry.amount),'method':entry.method,'reference':entry.reference,'at':entry.occurred_at.isoformat(),'actor':db.get(User,entry.actor_id).full_name if entry.actor_id else 'Chưa ghi người thu'}
