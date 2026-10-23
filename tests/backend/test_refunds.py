from decimal import Decimal
from datetime import datetime,timezone,timedelta
from sqlalchemy import select,func
from backend.models import User,MoneyEntry,FinancialAdjustment,Invoice,BookingStatus
from backend.schemas.inputs import ReceiptIn
from backend.api.refunds import CancellationIn,RefundIn
from backend.services.booking_service import create_booking
from backend.services.money_service import receipt,balance
from backend.services.refunds_service import settle_cancellation,refund
from tests.backend.test_booking_consistency import data,concurrent


def funded(db):
    b=create_booking(db,data());receipt(db,b.id,ReceiptIn(amount=1000000,request_key='refund-funding-key'),1)
    return b


def test_cancellation_keeps_original_invoice_and_refund_is_append_only(client,db):
    b=funded(db)
    assert client.put('/api/finance/policy',json={'cancellation_percent':20,'no_show_percent':50}).status_code==200
    payload={'reason':'Khách hủy chuyến','request_key':'cancel-funded-booking','target_status':'cancelled'}
    quoted=client.post(f'/api/finance/{b.id}/cancellation-preview',json=payload).json()
    assert Decimal(quoted['fee_amount'])==360000 and Decimal(quoted['refundable'])==640000
    payload['expected_fee']=quoted['fee_amount']
    assert client.post(f'/api/finance/{b.id}/cancellation',json=payload).status_code==200
    assert client.post(f'/api/finance/{b.id}/cancellation',json=payload).json()['replayed']
    db.refresh(b)
    assert b.status==BookingStatus.cancelled and db.scalar(select(Invoice.total))==1800000
    assert balance(db,b)['balance']==-640000
    refund_body={'amount':300000,'method':'bank_transfer','reason':'Hoàn một phần cọc','request_key':'partial-refund-key','reference':'REF-TEST'}
    first=client.post(f'/api/finance/{b.id}/refunds',json=refund_body)
    assert first.status_code==200
    assert client.post(f'/api/finance/{b.id}/refunds',json=refund_body).json()['id']==first.json()['id']
    assert db.scalar(select(func.count(MoneyEntry.id)))==2
    assert balance(db,b)['balance']==-340000
    f=client.get(f'/api/bookings/{b.id}/folio').json()
    assert Decimal(f['total'])==360000 and sum(Decimal(x['amount']) for x in f['lines'])==360000
    assert client.get(f'/bookings/{b.id}/finance').status_code==200


def test_refunds_serialize_and_do_not_refund_retained_fee(client,db):
    b=funded(db);bid=b.id
    client.put('/api/finance/policy',json={'cancellation_percent':20,'no_show_percent':50})
    user=db.get(User,1)
    settle_cancellation(db,bid,CancellationIn(reason='Khách hủy chuyến',request_key='cancel-concurrent-key',expected_fee=360000),user)
    def action(session,index):return refund(session,bid,RefundIn(amount=400000,reason='Hoàn cọc được duyệt',request_key=f'concurrent-refund-{index}'),session.get(User,1))
    assert sorted(concurrent(action))==[200,400]
    assert balance(db,b)['refunded']==400000


def test_no_show_settlement_respects_clock(client,db,monkeypatch):
    b=funded(db)
    body={'target_status':'no_show','reason':'Khách không liên lạc','request_key':'no-show-settlement','expected_fee':0}
    assert client.post(f'/api/finance/{b.id}/cancellation',json=body).status_code==409
    monkeypatch.setattr('backend.services.refunds_service.hotel_now',lambda:datetime(2030,1,10,23,tzinfo=timezone(timedelta(hours=7))))
    assert client.post(f'/api/finance/{b.id}/cancellation',json=body).status_code==200
