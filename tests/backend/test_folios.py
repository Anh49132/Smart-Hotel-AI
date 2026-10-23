from decimal import Decimal
from sqlalchemy import select,func
from backend.models import MoneyEntry,Role,User,Invoice
from backend.schemas.inputs import ReceiptIn
from backend.services.booking_service import create_booking,booking_action
from backend.services.money_service import receipt
from backend.services.invoice_service import invoice as calculate
from tests.backend.test_booking_consistency import data
from core.security import create_token,hash_password


def test_folio_charges_and_receipts_do_not_double_count(client,db):
    booking=create_booking(db,data())
    result=receipt(db,booking.id,ReceiptIn(amount=500000,request_key='folio-deposit-key'),1)
    calculate(booking.id,Decimal('100000'),db)
    response=client.get(f'/api/bookings/{booking.id}/folio')
    assert response.status_code==200
    f=response.json()
    assert sum(Decimal(x['amount']) for x in f['lines'])==Decimal(f['total'])==1700000
    assert f['received']=='500000.00' and f['balance']=='1200000.00'
    assert client.get(f'/bookings/{booking.id}/folio').status_code==200
    printed=client.get(f"/receipts/{result['id']}/print")
    assert printed.status_code==200 and 'Không phải hóa đơn điện tử' in printed.text
    assert '@media print' in printed.text
    assert db.scalar(select(func.count(MoneyEntry.id)))==1


def test_folio_access_and_own_deposit_receipt(client,db):
    booking=create_booking(db,data())
    user=User(username='receiptclerk',full_name='Clerk',role=Role.receptionist,password_hash=hash_password('Staff@123'))
    db.add(user);db.commit()
    r=receipt(db,booking.id,ReceiptIn(amount=100000,request_key='clerk-deposit-key'),user.id)
    client.cookies.set('access_token',create_token(user.id,'receptionist',user.token_version))
    assert client.get(f'/bookings/{booking.id}/folio').status_code==403
    assert client.get(f"/receipts/{r['id']}/print").status_code==200
    assert client.get('/api/bookings/999999/folio').status_code==403
