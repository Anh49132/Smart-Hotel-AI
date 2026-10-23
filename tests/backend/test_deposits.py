from decimal import Decimal
from sqlalchemy import select,func
from backend.models import MoneyEntry,Payment,Invoice
from backend.schemas.inputs import ReceiptIn
from backend.services.booking_service import create_booking,booking_action
from backend.services.money_service import receipt,balance
from backend.services.invoice_service import invoice as calculate
from tests.backend.test_booking_consistency import data,concurrent


def test_deposit_without_invoice_reconciles_once_on_checkout(client,db):
    booking=create_booking(db,data())
    body={'amount':'500000','method':'bank_transfer','reference':'REF-DEMO','request_key':'deposit-test-0001','kind':'deposit'}
    first=client.post(f'/api/bookings/{booking.id}/receipts',json=body)
    assert first.status_code==200 and not first.json()['replayed']
    repeated=client.post(f'/api/bookings/{booking.id}/receipts',json=body)
    assert repeated.json()['id']==first.json()['id'] and repeated.json()['replayed']
    body['amount']='600000'
    assert client.post(f'/api/bookings/{booking.id}/receipts',json=body).status_code==409
    assert not db.scalar(select(Invoice.id))
    booking_action(booking.id,'check-in',db);booking_action(booking.id,'check-out',db)
    inv=db.scalar(select(Invoice))
    assert inv.paid_amount==500000 and inv.total==1800000
    assert balance(db,booking)['balance']==1300000
    assert db.scalar(select(func.count(MoneyEntry.id)))==1 and db.scalar(select(func.count(Payment.id)))==0


def test_concurrent_deposits_cannot_overcollect(db):
    booking=create_booking(db,data());bid=booking.id
    assert sorted(concurrent(lambda session,index:receipt(session,bid,ReceiptIn(amount=1000000,request_key=f'concurrent-deposit-{index}'),1)))==[200,400]
    assert balance(db,booking)['net_received']==1000000


def test_simultaneous_same_key_creates_one_receipt(db):
    booking=create_booking(db,data());bid=booking.id
    assert concurrent(lambda session,index:receipt(session,bid,ReceiptIn(amount=500000,request_key='same-deposit-key'),1))==[200,200]
    assert db.scalar(select(func.count(MoneyEntry.id)))==1
