from decimal import Decimal
import pytest
from sqlalchemy import func, select
from backend.models import Booking, BookingNight, BookingStatusHistory, Invoice, Role, User
from backend.schemas import PaymentIn, ServiceUsageIn
from backend.services.booking_service import booking_action, create_booking
from backend.services.invoice_service import invoice as calculate, pay
from backend.services.services_service import use_service
from core.security import create_token, hash_password
from tests.backend.test_booking_consistency import data


def test_detail_is_read_only_and_handles_empty_sections(client, db):
    booking=create_booking(db,data(),actor_id=1)
    for _ in range(2):
        response=client.get(f'/api/bookings/{booking.id}')
        assert response.status_code==200
        body=response.json()
        assert body['code']==booking.code
        assert body['invoice'] is None and body['services']==[]
        assert body['estimate']['total']=='1800000.00'
        assert len(body['nightly_prices'])==2
        assert body['history'][0]['actor']=='Admin'
        html=client.get(f'/bookings/{booking.id}')
        assert html.status_code==200
        assert 'Chưa phát sinh dịch vụ' in html.text
        assert 'Chưa có hóa đơn' in html.text
    assert db.scalar(select(func.count(Invoice.id)))==0


def test_full_stay_detail_preserves_service_and_payment_records(client, db):
    booking=create_booking(db,data(),actor_id=1)
    booking_action(booking.id,'check-in',db,actor_id=1)
    use_service(ServiceUsageIn(booking_id=booking.id,service_id=1,quantity=2),db)
    booking_action(booking.id,'check-out',db,actor_id=1)
    invoice=db.scalar(select(Invoice).where(Invoice.booking_id==booking.id))
    pay(invoice.id,PaymentIn(amount=1000000),db,actor_id=1)
    body=client.get(f'/api/bookings/{booking.id}').json()
    assert body['invoice']['total']=='1900000.00'
    assert body['invoice']['remaining']=='900000.00'
    assert body['invoice']['finalized']
    assert body['services'][0]['total']=='100000.00'
    assert body['payments'][0]['actor']=='Admin'
    assert [h['to_status'] for h in body['history']]==['confirmed','checked_in','checked_out']
    assert not body['actions']['add_service'] and not body['actions']['check_out']
    assert body['actions']['pay']
    assert client.get(f'/bookings/{booking.id}').status_code==200


@pytest.mark.parametrize('role,frontdesk,finance',[(Role.admin,True,True),(Role.receptionist,True,False),(Role.accountant,False,True)])
def test_actions_and_history_follow_role(client, db, role, frontdesk, finance):
    booking=create_booking(db,data())
    booking_action(booking.id,'check-in',db)
    invoice=calculate(booking.id,None,db)
    pay(invoice.id,PaymentIn(amount=100000),db,actor_id=1)
    user=User(username='detailuser',full_name='Detail User',role=role,password_hash=hash_password('Staff@123'))
    db.add(user); db.commit()
    client.cookies.set('access_token',create_token(user.id,role.value,user.token_version))
    body=client.get(f'/api/bookings/{booking.id}').json()
    assert body['actions']['check_out']==frontdesk
    assert body['actions']['add_service']==frontdesk
    assert body['actions']['pay']==finance
    assert bool(body['payments'])==finance
    html=client.get(f'/bookings/{booking.id}').text
    assert ('id="detailServiceForm"' in html)==frontdesk
    assert ('id="detailPaymentForm"' in html)==finance
    assert ('<h2 class="h5">Lịch sử thu tiền</h2>' in html)==finance


def test_legacy_and_cancelled_details_and_missing_booking(client, db):
    booking=create_booking(db,data())
    for row in db.scalars(select(BookingNight).where(BookingNight.booking_id==booking.id)):
        db.delete(row)
    booking.booked_rate_source='legacy_current_rate'
    db.commit()
    booking_action(booking.id,'cancel',db,actor_id=1)
    body=client.get(f'/api/bookings/{booking.id}').json()
    assert body['nightly_prices']==[]
    assert not any(body['actions'].values())
    assert 'Dữ liệu cũ chưa lưu giá từng đêm' in client.get(f'/bookings/{booking.id}').text
    assert client.get('/api/bookings/999999').status_code==404
    assert client.get('/bookings/999999').status_code==404
    client.cookies.clear()
    assert client.get(f'/api/bookings/{booking.id}').status_code==401
    assert client.get(f'/bookings/{booking.id}',follow_redirects=False).status_code==303


def test_detail_escapes_notes_omits_sensitive_fields_and_marks_legacy_payment_gap(client, db):
    booking=create_booking(db,data())
    booking.note='<script>alert(1)</script>'
    db.commit()
    invoice=calculate(booking.id,None,db)
    invoice.paid_amount=Decimal('100000')
    db.commit()
    body=client.get(f'/api/bookings/{booking.id}').json()
    assert body['invoice']['ledger_gap']=='100000.00'
    assert 'identity_number' not in str(body) and 'password_hash' not in str(body)
    html=client.get(f'/bookings/{booking.id}').text
    assert '<script>alert(1)</script>' not in html
    assert '&lt;script&gt;' in html


def test_temporary_invoice_is_separate_from_current_service_estimate(client, db):
    booking=create_booking(db,data())
    booking_action(booking.id,'check-in',db)
    calculate(booking.id,Decimal('100000'),db)
    use_service(ServiceUsageIn(booking_id=booking.id,service_id=1,quantity=2),db)
    body=client.get(f'/api/bookings/{booking.id}').json()
    assert body['invoice']['total']=='1700000.00'
    assert body['estimate']['total']=='1800000.00'
