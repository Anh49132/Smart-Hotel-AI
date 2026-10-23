from decimal import Decimal
import pytest
from fastapi import HTTPException
from sqlalchemy import func, select
from backend.models import Booking, Invoice, Payment, PaymentStatus, RoomType
from backend.schemas import PaymentIn, ServiceUsageIn
from backend.services.booking_service import booking_action, create_booking
from backend.services.invoice_service import calculate_invoice, invoice as issue, pay
from backend.services.services_service import use_service
from tests.backend.test_booking_consistency import concurrent, data


def test_booked_rate_not_changed_by_new_list_price(db):
    booking=create_booking(db,data())
    db.get(RoomType,1).nightly_rate=1200000
    db.commit()
    invoice=calculate_invoice(db,booking)
    assert booking.booked_nightly_rate == Decimal('900000')
    assert invoice.room_amount == Decimal('1800000')


def test_checkout_keeps_discount_and_refreshes_new_services(db):
    booking=create_booking(db,data())
    booking_action(booking.id,'check-in',db)
    initial=issue(booking.id,Decimal('100000'),db)
    use_service(ServiceUsageIn(booking_id=booking.id,service_id=1,quantity=2),db)
    booking_action(booking.id,'check-out',db)
    db.refresh(initial)
    assert initial.discount == Decimal('100000')
    assert initial.service_amount == Decimal('100000')
    assert initial.total == Decimal('1800000')
    assert issue(booking.id,None,db).discount == Decimal('100000')


@pytest.mark.parametrize('discount',[Decimal('-1'),Decimal('1800001'),Decimal('0.001')])
def test_invalid_discount_rejected(db,discount):
    booking=create_booking(db,data())
    with pytest.raises(HTTPException):
        issue(booking.id,discount,db)


def test_cancelled_booking_not_invoiced(db):
    booking=create_booking(db,data())
    booking_action(booking.id,'cancel',db)
    with pytest.raises(HTTPException) as error:
        issue(booking.id,None,db)
    assert error.value.status_code == 409


def test_zero_total_is_paid_and_cannot_take_money(db):
    booking=create_booking(db,data())
    invoice=issue(booking.id,Decimal('1800000'),db)
    assert invoice.payment_status == PaymentStatus.paid
    with pytest.raises(HTTPException):
        pay(invoice.id,PaymentIn(amount=1),db,actor_id=1)


def test_cannot_discount_below_paid_or_cancel_invoiced_booking(db):
    booking=create_booking(db,data())
    invoice=issue(booking.id,None,db)
    pay(invoice.id,PaymentIn(amount=1000000),db,actor_id=1)
    with pytest.raises(HTTPException):
        issue(booking.id,Decimal('900000'),db)
    with pytest.raises(HTTPException):
        booking_action(booking.id,'cancel',db)


def test_concurrent_payments_cannot_overpay(db):
    booking=create_booking(db,data())
    invoice=issue(booking.id,None,db)
    invoice_id=invoice.id
    results=concurrent(lambda session,index:pay(invoice_id,PaymentIn(amount=1000000),session,actor_id=1))
    assert sorted(results)==[200,400]
    db.refresh(invoice)
    assert invoice.paid_amount == Decimal('1000000')
    assert db.scalar(select(func.sum(Payment.amount)).where(Payment.invoice_id==invoice_id)) == invoice.paid_amount


def test_payment_precision_rejected(client):
    assert client.post('/api/invoices/1/payments',json={'amount':1.001}).status_code == 422
