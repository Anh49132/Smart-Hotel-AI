from datetime import date
from decimal import Decimal
import pytest
from fastapi import HTTPException
from sqlalchemy import select
from backend.models import BookingNight, RatePlan, Role, RoomType, User
from backend.schemas import BookingIn, RoomTypeIn
from backend.schemas.inputs import RatePlanIn
from backend.services.rates_service import quote, save_rate_plan, update_room_type
from backend.services.booking_service import create_booking
from backend.services.invoice_service import calculate_invoice
from backend.services.ai_service import available_rooms
from core.security import create_token, hash_password
from tests.backend.test_booking_consistency import concurrent


def plan(start='2030-01-06', end='2030-01-07', price='1500000', active=True):
    return RatePlanIn(name='Lễ', start_date=start, end_date=end, nightly_rate=price, is_active=active)


def test_weekend_special_priority_and_checkout_exclusive(db):
    room_type = db.get(RoomType, 1)
    room_type.weekend_rate = Decimal('1100000')
    db.commit()
    save_rate_plan(db, 1, plan())
    prices = quote(db, room_type, date(2030,1,4), date(2030,1,8))
    assert [n['amount'] for n in prices['nights']] == [900000,1100000,1500000,900000]
    assert prices['total'] == Decimal('4400000')
    assert prices['nights'][-1]['source'] == 'Giá thường'


def test_booking_snapshots_survive_all_price_changes(db):
    room_type = db.get(RoomType,1)
    room_type.weekend_rate = Decimal('1100000')
    db.commit()
    special = save_rate_plan(db,1,plan())
    booking = create_booking(db,BookingIn(customer_id=1,room_id=1,check_in='2030-01-04',check_out='2030-01-08',guests=2))
    snapshot = db.scalars(select(BookingNight).where(BookingNight.booking_id==booking.id)).all()
    assert len(snapshot) == 4
    room_type.nightly_rate=2000000
    room_type.weekend_rate=3000000
    special.nightly_rate=4000000
    special.name='Đã đổi tên'
    db.commit()
    invoice = calculate_invoice(db, booking)
    assert invoice.room_amount == Decimal('4400000')
    assert [n.source for n in snapshot if n.stay_date==date(2030,1,6)] == ['Lễ']


def test_overlapping_plans_rejected_but_adjacent_allowed(db):
    save_rate_plan(db,1,plan())
    with pytest.raises(HTTPException) as error:
        save_rate_plan(db,1,plan(start='2030-01-05'))
    assert error.value.status_code == 409
    save_rate_plan(db,1,plan(start='2030-01-07',end='2030-01-08'))
    save_rate_plan(db,1,plan(active=False))


def test_concurrent_special_rates_cannot_overlap(db):
    assert sorted(concurrent(lambda session,index:save_rate_plan(session,1,plan()))) == [200,409]


def test_inactive_type_hidden_from_booking_and_ai(client, db):
    booking = create_booking(db,BookingIn(customer_id=1,room_id=1,check_in='2030-01-10',check_out='2030-01-12',guests=2))
    update_room_type(db,1,RoomTypeIn(name='Deluxe',capacity=2,nightly_rate=900000,is_active=False))
    assert client.get('/api/rooms?check_in=2030-02-01&check_out=2030-02-03').json()==[]
    assert available_rooms(db,date(2030,2,1),date(2030,2,3),2,Decimal('5000000'))==[]
    assert client.post('/api/bookings',json={'customer_id':1,'room_id':1,'check_in':'2030-02-01','check_out':'2030-02-03','guests':2}).status_code==409
    assert calculate_invoice(db,booking).room_amount==1800000
    assert client.delete('/api/room-types/1').status_code==409


def test_capacity_price_validation_and_permissions(client, db):
    create_booking(db,BookingIn(customer_id=1,room_id=1,check_in='2030-01-10',check_out='2030-01-12',guests=2))
    assert client.put('/api/room-types/1',json={'name':'Deluxe','capacity':1,'nightly_rate':900000}).status_code==409
    assert client.post('/api/room-types/1/rate-plans',json={'name':'Bad','start_date':'2030-01-01','end_date':'2030-01-01','nightly_rate':100}).status_code==422
    assert client.get('/api/room-types/1/quote?check_in=2030-01-01&check_out=2032-01-01').status_code==422
    assert client.get('/rates').status_code==200
    assert client.get('/api/room-types/999/quote?check_in=2030-01-01&check_out=2030-01-02').status_code==404
    user=User(username='reception',full_name='Reception',role=Role.receptionist,password_hash=hash_password('Staff@123'))
    db.add(user); db.commit()
    client.cookies.set('access_token',create_token(user.id,user.role.value,user.token_version))
    assert client.get('/rates').status_code==403
    assert client.put('/api/room-types/1',json={'name':'Deluxe','capacity':2,'nightly_rate':900000}).status_code==403


def test_ai_budget_checks_each_night_and_quote_matches_availability(client, db):
    db.get(RoomType,1).weekend_rate=Decimal('1500000'); db.commit()
    assert available_rooms(db,date(2030,1,4),date(2030,1,6),2,Decimal('1000000'))==[]
    rooms=client.get('/api/rooms?check_in=2030-01-04&check_out=2030-01-06').json()
    prices=client.get('/api/room-types/1/quote?check_in=2030-01-04&check_out=2030-01-06').json()
    assert Decimal(str(rooms[0]['stay_total']))==Decimal(str(prices['total']))==2400000


def test_missing_snapshot_rejected_instead_of_repricing(db):
    booking=create_booking(db,BookingIn(customer_id=1,room_id=1,check_in='2030-01-10',check_out='2030-01-12',guests=2))
    row=db.scalar(select(BookingNight).where(BookingNight.booking_id==booking.id))
    db.delete(row); db.commit()
    with pytest.raises(HTTPException):
        calculate_invoice(db,booking)
