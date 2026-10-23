"""Explicit fake demo fixture. Re-runs never reset passwords, dates or financial data."""
import json
from datetime import datetime,time,timedelta,timezone
from decimal import Decimal
from sqlalchemy import select,text,update
from fastapi import HTTPException
from backend.models import DemoSeed,User,Role,RoomType,Room,RoomStatus,Customer,Booking,BookingStatus,BookingNight,RoomStay,BookingStatusHistory,HotelService,ServiceUsage,Invoice,Payment,MoneyEntry,FinancialAdjustment,CashierShift,CleaningTask,RoomBlock,PaymentStatus,HotelPolicy
from core.security import hash_password
from core.hotel_time import hotel_today
from .transactions import write_transaction

def stamp(day,hour=11):return datetime.combine(day,time(hour),timezone(timedelta(hours=7))).astimezone(timezone.utc).replace(tzinfo=None)

def seed_demo(db,password,anchor=None):
    if len(password)<12 or len(password.encode('utf-8'))>72:raise ValueError('Demo requires a private password (12+ chars, <=72 UTF-8 bytes)')
    anchor=anchor or hotel_today()
    with write_transaction(db):
        if db.get_bind().dialect.name=='postgresql':db.execute(text('SELECT pg_advisory_xact_lock(3318027022)'))
        else:db.execute(update(User).values(id=User.id))
        if db.get(DemoSeed,'lotus-demo-v1'):db.rollback();return {'already_seeded':True}
        # Do not inject fake fixtures into an operational hotel by accident.
        if db.scalar(select(Booking.id).limit(1)) or db.scalar(select(Room.id).limit(1)):raise HTTPException(409,'Demo seed chỉ chạy vào khách sạn chưa có phòng/booking; không ghi đè dữ liệu hiện có')
        if not db.get(HotelPolicy,1):db.add(HotelPolicy(id=1,cancellation_percent=10,no_show_percent=0))
        users={}
        for role in (Role.receptionist,Role.accountant,Role.housekeeping):
            username='demo_'+role.value
            if db.scalar(select(User.id).where(User.username==username)):raise HTTPException(409,'Tên tài khoản demo đã tồn tại; không đổi quyền hoặc mật khẩu của tài khoản cũ')
            user=User(username=username,full_name='DEMO '+role.value,role=role,password_hash=hash_password(password),must_change_password=True)
            db.add(user);db.flush();users[role]=user
        types=[]
        for name,capacity,price in [('Standard',2,650000),('Deluxe',2,850000),('Family',4,1250000)]:
            item=RoomType(name='DEMO '+name,capacity=capacity,nightly_rate=price,amenities='WiFi, Bồn tắm' if name!='Standard' else 'WiFi');db.add(item);db.flush();types.append(item)
        rooms=[]
        for i in range(12):
            room=Room(number=f'D{301+i}',floor=3,room_type_id=types[i%3].id);db.add(room);db.flush();rooms.append(room)
        customers=[]
        for i in range(8):
            c=Customer(full_name=f'Khách Demo {i+1:02}',phone=f'00000000{i:02}');db.add(c);db.flush();customers.append(c)
        service=HotelService(name='DEMO Giặt là',unit='kg',price=50000);db.add_all([service,HotelService(name='DEMO Ăn sáng',unit='suất',price=100000),HotelService(name='DEMO Đưa đón',unit='chuyến',price=300000)]);db.flush()
        actor=users[Role.accountant].id
        shift=CashierShift(cashier_id=actor,status='closed',opening_cash=0,counted_cash=0,expected_cash=0,difference=0,opened_at=stamp(anchor-timedelta(days=40),8),closed_at=stamp(anchor,8),note='Ca tổng hợp dữ liệu giả để minh họa; không phải ca thực tế')
        db.add(shift);db.flush();cash_in=Decimal(0);cash_out=Decimal(0)
        def booking(code,room_index,offset,nights,status='confirmed'):
            room=rooms[room_index];rate=types[room_index%3].nightly_rate
            start=anchor+timedelta(days=offset);end=start+timedelta(days=nights)
            b=Booking(code='DEMO-'+code,customer_id=customers[room_index%8].id,room_id=room.id,check_in=start,check_out=end,guests=2,booked_nightly_rate=rate,booked_rate_source='demo_snapshot',status=BookingStatus(status),note='Dữ liệu giả phục vụ báo cáo',created_at=stamp(min(start-timedelta(days=3),anchor-timedelta(days=3)),10))
            if status in ('checked_in','checked_out'):b.actual_check_in=stamp(start,14)
            if status=='checked_out':b.actual_check_out=stamp(end,11)
            db.add(b);db.flush()
            db.add(RoomStay(booking_id=b.id,room_id=room.id,check_in=start,check_out=end))
            db.add_all([BookingNight(booking_id=b.id,stay_date=start+timedelta(days=i),amount=rate,source='DEMO giá mẫu') for i in range(nights)])
            states=['confirmed']+(['checked_in'] if status in ('checked_in','checked_out') else [])+(['checked_out'] if status=='checked_out' else [status] if status in ('cancelled','no_show') else [])
            previous=None
            for state in states:
                db.add(BookingStatusHistory(booking_id=b.id,from_status=BookingStatus(previous) if previous else None,to_status=BookingStatus(state),changed_by=users[Role.receptionist].id,changed_at=b.created_at if state=='confirmed' else b.actual_check_in if state=='checked_in' else b.actual_check_out if state=='checked_out' else stamp(anchor-timedelta(days=1)) if state=='cancelled' else stamp(start,23)));previous=state
            return b,Decimal(rate)*nights
        def money(b,amount,kind,when,inv=None):
            nonlocal cash_in,cash_out
            mirror=None
            if kind=='payment':
                mirror=Payment(invoice_id=inv.id,amount=amount,paid_by=actor,paid_at=stamp(when));db.add(mirror);db.flush()
            db.add(MoneyEntry(booking_id=b.id,payment_id=mirror.id if mirror else None,amount=amount,kind=kind,method='bank_transfer',reference='DEMO-NO-BANK',request_key=f'demo-{b.id}-{kind}',actor_id=actor,shift_id=shift.id,occurred_at=stamp(when)))
            if kind=='refund':cash_out+=amount
            else:cash_in+=amount
        for number,offset,room_index in [('PAST01',-35,0),('STAY01',-4,1)]:
            b,total=booking(number,room_index,offset,2,'checked_out')
            db.add(ServiceUsage(booking_id=b.id,service_id=service.id,quantity=1,unit_price=50000,used_at=stamp(b.check_in,18)))
            inv=Invoice(booking_id=b.id,room_amount=total,service_amount=50000,total=total+50000,paid_amount=total+50000,payment_status=PaymentStatus.paid,issued_at=stamp(b.check_out));db.add(inv);db.flush();money(b,total+50000,'payment',b.check_out,inv)
        b,_=booking('IN01',2,-1,3,'checked_in');rooms[2].status=RoomStatus.occupied;money(b,500000,'deposit',anchor-timedelta(days=2))
        b,_=booking('TODAY',3,0,2);money(b,300000,'deposit',anchor-timedelta(days=1))
        b,total=booking('CANCEL',4,3,2,'cancelled')
        inv=Invoice(booking_id=b.id,room_amount=total,total=total,paid_amount=170000,payment_status=PaymentStatus.paid,issued_at=stamp(anchor-timedelta(days=1)));db.add(inv);db.flush()
        money(b,500000,'deposit',anchor-timedelta(days=2));money(b,330000,'refund',anchor-timedelta(days=1))
        db.add(FinancialAdjustment(booking_id=b.id,target_status='cancelled',original_total=total,fee_amount=170000,percent=10,amount=Decimal(170000)-total,reason='DEMO: phí hủy 10%, đã hoàn phần dư',request_key='demo-cancel-adjustment',actor_id=actor,created_at=stamp(anchor-timedelta(days=1))))
        booking('NOSHOW',5,-2,2,'no_show')
        rooms[6].status=RoomStatus.cleaning;db.add(CleaningTask(room_id=rooms[6].id,assigned_to=users[Role.housekeeping].id,created_at=stamp(anchor,8)))
        db.add(RoomBlock(room_id=rooms[7].id,start_date=anchor,end_date=anchor+timedelta(days=4),description='DEMO: bảo trì điều hòa',created_by=users[Role.receptionist].id))
        for day in range(1,15):booking(f'FUTURE{day:02}',8+((day-1)%2),day,2)
        booking('NEXTMONTH',10,35,2)
        shift.snapshot_json=json.dumps({'cash':{'in':'0.00','out':'0.00'},'bank_transfer':{'in':str(cash_in),'out':str(cash_out)},'expected_cash':'0.00','pending':{'staying':1,'cleaning':1}},ensure_ascii=False)
        db.add(DemoSeed(name='lotus-demo-v1',anchor_date=anchor));db.commit()
        return {'already_seeded':False,'rooms':12,'bookings':21,'staff':3,'anchor':str(anchor)}
