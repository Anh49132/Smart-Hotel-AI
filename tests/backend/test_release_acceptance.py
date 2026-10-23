"""Acceptance workflow spans staff roles, room moves, payments and reports."""
import json
from decimal import Decimal
from datetime import datetime,timezone,timedelta
from unittest.mock import AsyncMock
from sqlalchemy import select,event
import pytest
from backend.models import User,Role,Room,Invoice,MoneyEntry,CleaningTask,RoomStatus
from core.security import hash_password,create_token

@pytest.fixture
def ledger_clock():
    def stamp(mapper,connection,target):
        from core.hotel_time import hotel_now
        value=hotel_now().astimezone(timezone.utc).replace(tzinfo=None)
        if isinstance(target,Invoice):target.issued_at=value
        else:target.occurred_at=value
    for model in (Invoice,MoneyEntry):event.listen(model,'before_insert',stamp)
    yield
    for model in (Invoice,MoneyEntry):event.remove(model,'before_insert',stamp)

def as_user(client,user):
    client.cookies.set('access_token',create_token(user.id,user.role.value,user.token_version))

def test_complete_stay_roles_room_move_payments_and_cleaning(client,db,monkeypatch,ledger_clock):
    people={role:User(username=role.value,full_name=role.value,password_hash=hash_password('Demo@123'),role=role) for role in (Role.receptionist,Role.accountant,Role.housekeeping)}
    db.add_all([*people.values(),Room(id=2,number='303',floor=3,room_type_id=1)]);db.commit()
    clerk,accountant,cleaner=(people[r] for r in (Role.receptionist,Role.accountant,Role.housekeeping))
    as_user(client,clerk)
    monkeypatch.setattr('backend.services.room_advice.generate_structured',AsyncMock(return_value=json.dumps({'recommendations':[{'room_id':1,'stay_total':'1800000.00','reason_codes':['budget','capacity']}]})))
    assert client.post('/api/ai/room-advice',json={'guests':2,'budget':900000,'check_in':'2030-01-10','check_out':'2030-01-12'}).json()['validated']
    booking=client.post('/api/bookings',json={'customer_id':1,'room_id':1,'check_in':'2030-01-10','check_out':'2030-01-12','guests':2}).json();bid=booking['id']
    deposit={'amount':500000,'request_key':'acceptance-deposit'}
    first=client.post(f'/api/bookings/{bid}/receipts',json=deposit).json()
    assert client.post(f'/api/bookings/{bid}/receipts',json=deposit).json()['id']==first['id']
    assert client.post(f'/api/bookings/{bid}/check-in').status_code==200
    assert client.post('/api/service-usages',json={'booking_id':bid,'service_id':1,'quantity':2}).status_code==200
    now=lambda:datetime(2030,1,11,10,tzinfo=timezone(timedelta(hours=7)))
    monkeypatch.setattr('core.hotel_time.hotel_now',now);monkeypatch.setattr('backend.services.frontdesk_service.hotel_now',now)
    change={'room_id':2,'check_in':'2030-01-10','check_out':'2030-01-13','reason':'Khách muốn đổi phòng và ở thêm'}
    quoted=client.post(f'/api/booking-changes/{bid}/preview',json=change)
    assert quoted.status_code==200
    assert client.put(f'/api/bookings/{bid}',json=dict(change,expected_total=quoted.json()['new_room_total'])).status_code==200
    now=lambda:datetime(2030,1,13,11,tzinfo=timezone(timedelta(hours=7)))
    monkeypatch.setattr('core.hotel_time.hotel_now',now);monkeypatch.setattr('backend.services.frontdesk_service.hotel_now',now)
    assert client.post(f'/api/bookings/{bid}/check-out').status_code==200
    inv=db.scalar(select(Invoice).where(Invoice.booking_id==bid));assert inv.total==2800000
    as_user(client,accountant)
    assert client.post(f'/api/invoices/{inv.id}/payments',json={'amount':2300000,'request_key':'acceptance-final-pay'}).status_code==200
    folio=client.get(f'/api/bookings/{bid}/folio').json()
    assert Decimal(folio['balance'])==0 and Decimal(folio['total'])==2800000
    assert sum(Decimal(line['amount']) for line in folio['lines'])==2800000
    report=client.get('/api/reports/operations?start=2030-01-10&end=2030-01-14').json()
    assert report['allocated_nights']==3 and report['occupancy']==37.5
    assert Decimal(str(report['net_cash']))==2800000 and Decimal(str(report['invoice_net']))==2800000
    as_user(client,clerk)
    tasks=db.scalars(select(CleaningTask).order_by(CleaningTask.id)).all();assert len(tasks)==2
    for task in tasks:assert client.post(f'/api/housekeeping/{task.id}',json={'action':'assign','assigned_to':cleaner.id}).status_code==200
    as_user(client,cleaner)
    assert client.get(f'/api/bookings/{bid}').status_code==403
    for task in tasks:
        assert client.post(f'/api/housekeeping/{task.id}',json={'action':'start'}).status_code==200
        assert client.post(f'/api/housekeeping/{task.id}',json={'action':'complete'}).status_code==200
    as_user(client,clerk)
    for task in tasks:assert client.post(f'/api/housekeeping/{task.id}',json={'action':'inspect'}).status_code==200
    db.expire_all();assert all(r.status==RoomStatus.available for r in db.scalars(select(Room)))


@pytest.mark.parametrize('role',list(Role))
def test_finance_and_ai_permission_matrix(client,db,role):
    user=User(username='matrix',full_name='Matrix',role=role,password_hash=hash_password('Demo@123'));db.add(user);db.commit();as_user(client,user)
    allowed=role in (Role.admin,Role.accountant)
    assert client.get('/api/reports/operations?start=2030-01-01&end=2030-02-01').status_code==(200 if allowed else 403)
    assert client.get('/api/finance/policy').status_code==(200 if allowed else 403)
    assert client.get('/api/receipts/999999').status_code==(403 if role==Role.housekeeping else 404)
