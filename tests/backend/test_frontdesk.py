from datetime import datetime,timezone,timedelta
from sqlalchemy import select
from backend.models import Booking,BookingStatus,Invoice
from backend.services.booking_service import create_booking,booking_action
from backend.services.invoice_service import invoice as calculate
from tests.backend.test_booking_consistency import data


def now(monkeypatch,hour,day=10):
    monkeypatch.setattr('backend.services.frontdesk_service.hotel_now',lambda:datetime(2030,1,day,hour,tzinfo=timezone(timedelta(hours=7))))


def test_no_show_gate_distinct_status_and_inventory(client,db,monkeypatch):
    booking=create_booking(db,data())
    now(monkeypatch,22)
    assert client.post(f'/api/frontdesk/{booking.id}/no-show').status_code==409
    now(monkeypatch,23)
    assert client.post(f'/api/frontdesk/{booking.id}/no-show').status_code==200
    db.refresh(booking)
    assert booking.status==BookingStatus.no_show
    assert client.get('/api/rooms?check_in=2030-01-10&check_out=2030-01-12').json()
    assert client.post(f'/api/invoices/{booking.id}/calculate').status_code==409


def test_arrival_outside_booked_date_rejected(client,db,monkeypatch):
    booking=create_booking(db,data(11))
    assert client.post(f'/api/bookings/{booking.id}/check-in').status_code==409
    assert client.put('/api/frontdesk/policy',json={'check_in_hour':14,'check_out_hour':12,'no_show_hour':9,'early_fee':0,'late_fee':0}).status_code==422


def test_surcharge_is_manual_snapshot_once_and_included_in_invoice(client,db,monkeypatch):
    now(monkeypatch,9)
    assert client.put('/api/frontdesk/policy',json={'check_in_hour':14,'check_out_hour':12,'no_show_hour':23,'early_fee':'100000','late_fee':'200000'}).status_code==200
    booking=create_booking(db,data())
    frontdesk=client.get('/frontdesk')
    assert frontdesk.status_code==200
    assert 'BẢN DEMO' not in frontdesk.text
    assert calculate(booking.id,None,db).total==1800000
    assert client.post(f'/api/frontdesk/{booking.id}/surcharges',json={'kind':'early','expected_amount':'99999'}).status_code==409
    assert client.post(f'/api/frontdesk/{booking.id}/surcharges',json={'kind':'early','expected_amount':'100000'}).status_code==200
    assert client.post(f'/api/frontdesk/{booking.id}/surcharges',json={'kind':'early','expected_amount':'100000'}).status_code==409
    invoice=db.scalar(select(Invoice).where(Invoice.booking_id==booking.id));db.refresh(invoice)
    assert invoice.surcharge_amount==100000 and invoice.total==1900000
    booking_action(booking.id,'check-in',db)
    now(monkeypatch,13,12)
    assert client.get('/api/frontdesk').json()['rows'][0]['overdue']
    assert client.post(f'/api/frontdesk/{booking.id}/surcharges',json={'kind':'late','expected_amount':'200000'}).status_code==200
    booking_action(booking.id,'check-out',db)
    db.refresh(invoice);db.refresh(booking)
    assert invoice.total==2100000 and booking.actual_check_in and booking.actual_check_out
    assert client.get(f'/bookings/{booking.id}').status_code==200
