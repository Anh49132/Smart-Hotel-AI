"""Reports keep invoice, adjustment, and cash event dates separate."""
import csv
import io
from datetime import datetime,time,timedelta,timezone
from decimal import Decimal
from fastapi import HTTPException
from sqlalchemy import select,func,case
from backend.models import Room,RoomBlock,RoomStay,Booking,BookingStatus,Invoice,FinancialAdjustment,MoneyEntry

HOTEL_TZ=timezone(timedelta(hours=7))

def local_date(value):
    return value.replace(tzinfo=timezone.utc).astimezone(HOTEL_TZ).date()

def utc_boundary(day):
    return datetime.combine(day,time(),HOTEL_TZ).astimezone(timezone.utc).replace(tzinfo=None)

def room_days(room_id,start,end):
    return {(room_id,start+timedelta(days=i)) for i in range(max(0,(end-start).days))}

def operating_report(db,start,end):
    if not 1<=(end-start).days<=366:raise HTTPException(422,'Khoảng báo cáo phải từ 1 đến 366 ngày; ngày kết thúc không bao gồm')
    room_count=db.scalar(select(func.count()).select_from(Room))
    capacity=room_count*(end-start).days
    blocked=set()
    for b in db.scalars(select(RoomBlock).where(RoomBlock.status!='cancelled',RoomBlock.start_date<end,RoomBlock.end_date>start)):
        stop=b.end_date
        if b.status=='resolved' and b.resolved_at:stop=min(stop,local_date(b.resolved_at))
        blocked|=room_days(b.room_id,max(start,b.start_date),min(end,stop))
    bookings=db.scalars(select(Booking).where(Booking.status.not_in((BookingStatus.cancelled,BookingStatus.no_show)),Booking.check_in<end,Booking.check_out>start)).all()
    booking_ids={b.id for b in bookings}
    stays=db.scalars(select(RoomStay).where(RoomStay.booking_id.in_(booking_ids))).all() if booking_ids else []
    segmented={s.booking_id for s in stays}
    allocated=set()
    for s in stays:allocated|=room_days(s.room_id,max(start,s.check_in),min(end,s.check_out))
    for b in bookings:
        if b.id not in segmented:allocated|=room_days(b.room_id,max(start,b.check_in),min(end,b.check_out))
    usable=capacity-len(blocked)
    lo,hi=utc_boundary(start),utc_boundary(end)
    def summed(column,clock):return db.scalar(select(func.coalesce(func.sum(column),0)).where(clock>=lo,clock<hi))
    invoiced=summed(Invoice.total,Invoice.issued_at)
    adjustments=summed(FinancialAdjustment.amount,FinancialAdjustment.created_at)
    cash={m:{'in':Decimal(0),'out':Decimal(0)} for m in ('cash','bank_transfer','unknown')}
    deposits=Decimal(0);legacy_opening=Decimal(0)
    for e in db.scalars(select(MoneyEntry).where(MoneyEntry.occurred_at>=lo,MoneyEntry.occurred_at<hi)):
        if e.kind=='legacy_opening':legacy_opening+=e.amount;continue
        cash[e.method]['out' if e.kind=='refund' else 'in']+=e.amount
        if e.kind=='deposit':deposits+=e.amount
    received=sum((v['in'] for v in cash.values()),Decimal(0))
    refunded=sum((v['out'] for v in cash.values()),Decimal(0))
    # Current balances cannot reconstruct a historical receivables snapshot.
    net_by_booking=dict(db.execute(select(MoneyEntry.booking_id,func.sum(case((MoneyEntry.kind=='refund',-MoneyEntry.amount),else_=MoneyEntry.amount))).group_by(MoneyEntry.booking_id)).all())
    adjustment_by_booking=dict(db.execute(select(FinancialAdjustment.booking_id,FinancialAdjustment.amount)).all())
    receivable=Decimal(0);credit=Decimal(0);invoiced_ids=set()
    for inv in db.scalars(select(Invoice)):
        invoiced_ids.add(inv.booking_id)
        due=inv.total+adjustment_by_booking.get(inv.booking_id,0)-net_by_booking.get(inv.booking_id,0)
        receivable+=max(Decimal(0),due);credit+=max(Decimal(0),-due)
    unallocated=sum((amount for bid,amount in net_by_booking.items() if bid not in invoiced_ids),Decimal(0))
    return {'start':start,'end':end,'room_count':room_count,'capacity_nights':capacity,'blocked_nights':len(blocked),'sellable_nights':usable,'allocated_nights':len(allocated),'occupancy':round(100*len(allocated)/usable,2) if usable else 0,'inventory_conflicts':len(allocated&blocked),'booking_count':len(bookings),'confirmed_count':sum(b.status==BookingStatus.confirmed for b in bookings),'invoice_gross':invoiced,'adjustments':adjustments,'invoice_net':invoiced+adjustments,'received':received,'refunded':refunded,'net_cash':received-refunded,'deposits':deposits,'legacy_opening_excluded':legacy_opening,'cash':cash,'receivables_now':receivable,'credits_now':credit,'deposits_unallocated_now':unallocated}

def report_csv(report):
    output=io.StringIO(newline='');writer=csv.writer(output)
    writer.writerow(['metric','value'])
    for key,value in report.items():
        if key=='cash':
            for method,totals in value.items():
                for direction,amount in totals.items():writer.writerow([f'{method}_{direction}',str(amount)])
        else:writer.writerow([key,str(value)])
    return '\ufeff'+output.getvalue()
