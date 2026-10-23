from datetime import datetime,timezone,timedelta
from backend.models import Role
from backend.services.booking_service import create_booking
from tests.backend.test_booking_consistency import data
from tests.backend.test_staff_security import staff,token


def test_fee_policy_cannot_be_bypassed_by_quick_actions(client,db,monkeypatch):
    b=create_booking(db,data())
    client.put('/api/finance/policy',json={'cancellation_percent':20,'no_show_percent':50})
    assert client.post(f'/api/bookings/{b.id}/cancel').status_code==409
    monkeypatch.setattr('backend.services.frontdesk_service.hotel_now',lambda:datetime(2030,1,10,23,tzinfo=timezone(timedelta(hours=7))))
    assert client.post(f'/api/frontdesk/{b.id}/no-show').status_code==409


def test_reception_cannot_refund_settle_or_close_someone_elses_shift(client,db):
    b=create_booking(db,data());user=staff(db,Role.receptionist)
    client.cookies.set('access_token',token(user))
    assert client.post(f'/api/finance/{b.id}/refunds',json={'amount':1,'reason':'Test permission','request_key':'test-permission-refund'}).status_code==403
    assert client.get('/api/finance/policy').status_code==403
    assert client.get('/reports').status_code==403
    assert client.post('/api/shifts/1/close',json={'counted_cash':0,'note':'Cannot close other shift'}).status_code==403
    assert client.post(f'/api/bookings/{b.id}/receipts',json={'amount':1,'request_key':'no-shift-deposit'}).status_code==409


def test_bank_deposit_does_not_fund_cash_drawer(client,db):
    b=create_booking(db,data())
    assert client.post(f'/api/bookings/{b.id}/receipts',json={'amount':100000,'method':'bank_transfer','request_key':'bank-deposit-only'}).status_code==200
    response=client.post(f'/api/finance/{b.id}/refunds',json={'amount':1,'reason':'Hoàn sai phương thức thử nghiệm','request_key':'cash-not-in-drawer'})
    assert response.status_code==409 and 'tiền mặt' in response.json()['detail']
