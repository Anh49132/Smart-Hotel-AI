from decimal import Decimal
from sqlalchemy import select
from backend.models import CashierShift,MoneyEntry,User
from backend.schemas.inputs import ReceiptIn
from backend.services.booking_service import create_booking
from backend.services.money_service import receipt
from backend.services.shifts_service import close_shift
from backend.api.shifts import CloseShiftIn
from tests.backend.test_booking_consistency import data,concurrent


def test_close_snapshots_methods_and_blocks_new_money(client,db):
    b=create_booking(db,data())
    cash={'amount':500000,'request_key':'cash-in-before-close'}
    assert client.post(f'/api/bookings/{b.id}/receipts',json=cash).status_code==200
    assert client.post(f'/api/bookings/{b.id}/receipts',json={'amount':100000,'method':'bank_transfer','request_key':'bank-in-before-close'}).status_code==200
    assert client.post(f'/api/finance/{b.id}/refunds',json={'amount':100000,'reason':'Khách điều chỉnh tiền cọc','request_key':'cash-refund-before-close'}).status_code==200
    shift=db.scalar(select(CashierShift))
    body={'counted_cash':390000,'note':'Giao ca, còn một lịch đang chờ khách'}
    response=client.post(f'/api/shifts/{shift.id}/close',json=body)
    assert response.status_code==200 and Decimal(response.json()['difference'])==-10000
    closed=client.get('/api/shifts').json()[0]
    assert Decimal(closed['totals']['expected_cash'])==400000
    assert Decimal(closed['totals']['bank_transfer']['in'])==100000
    assert client.post('/api/shifts/1/close',json=body).status_code==409
    assert client.post(f'/api/bookings/{b.id}/receipts',json=cash).json()['replayed']
    assert client.post(f'/api/bookings/{b.id}/receipts',json=dict(cash,request_key='new-after-closed-key')).status_code==409
    assert client.post('/api/shifts',json={'opening_cash':400000}).status_code==200
    assert client.post('/api/shifts',json={'opening_cash':0}).status_code==409
    assert client.get('/api/shifts').json()[1]==closed
    assert client.get('/shifts').status_code==200


def test_close_and_receipt_are_serialized(db):
    b=create_booking(db,data());bid=b.id
    def work(session,index):
        if index==0:receipt(session,bid,ReceiptIn(amount=100000,request_key='close-race-receipt'),1)
        else:close_shift(session,1,session.get(User,1),CloseShiftIn(counted_cash=0,note='Bàn giao ca thử nghiệm'))
    results=concurrent(work)
    assert results[1]==200 and results[0] in (200,409)
    db.expire_all();shift=db.get(CashierShift,1)
    received=db.scalar(select(MoneyEntry.amount).where(MoneyEntry.shift_id==1)) or Decimal(0)
    assert shift.expected_cash==received
