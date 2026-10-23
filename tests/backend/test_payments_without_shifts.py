from decimal import Decimal
from sqlalchemy import select,func
from backend.models import CashierShift,MoneyEntry
from backend.services.booking_service import create_booking
from tests.backend.test_booking_consistency import data


def test_shift_ui_api_and_ai_are_removed(client):
    assert 'href="/shifts"' not in client.get('/').text
    assert client.get('/shifts').status_code==404
    assert client.get('/api/shifts').status_code==404
    assert client.post('/api/shifts',json={'opening_cash':0}).status_code==404
    assert client.post('/api/shifts/1/close',json={}).status_code==404
    assert client.post('/api/ai/handover/1',json={}).status_code==404


def test_legacy_closed_shift_is_preserved_and_does_not_block_money(client,db):
    booking=create_booking(db,data())
    legacy=CashierShift(cashier_id=1,status='closed',opening_cash=0,counted_cash=100000,expected_cash=100000,difference=0,note='Historical record',snapshot_json='{"legacy":true}')
    db.add(legacy);db.flush()
    old=MoneyEntry(booking_id=booking.id,amount=100000,kind='deposit',method='cash',request_key='legacy-shift-receipt',actor_id=1,shift_id=legacy.id)
    db.add(old);db.commit();old_id=old.id;shift_id=legacy.id
    body={'amount':50000,'request_key':'direct-receipt-no-shift'}
    received=client.post(f'/api/bookings/{booking.id}/receipts',json=body)
    assert received.status_code==200
    assert client.post(f'/api/bookings/{booking.id}/receipts',json=body).json()['replayed']
    refunded=client.post(f'/api/finance/{booking.id}/refunds',json={'amount':10000,'reason':'Hoàn theo yêu cầu khách','request_key':'direct-refund-no-shift'})
    assert refunded.status_code==200
    db.expire_all()
    assert db.get(MoneyEntry,old_id).shift_id==shift_id
    assert db.get(CashierShift,shift_id).snapshot_json=='{"legacy":true}'
    assert db.get(CashierShift,shift_id).status=='closed'
    assert db.scalar(select(func.count()).select_from(CashierShift))==1
    assert db.get(MoneyEntry,received.json()['id']).shift_id is None
    assert db.get(MoneyEntry,refunded.json()['id']).shift_id is None
    assert Decimal(client.get(f'/api/bookings/{booking.id}/balance').json()['net_received'])==140000
