from decimal import Decimal
import pytest
from fastapi import HTTPException
from sqlalchemy import select,func
from backend.models import Booking,BookingNight,BookingChange,Room,RoomStay
from backend.schemas import BookingIn,PaymentIn
from backend.schemas.inputs import BookingChangeIn
from backend.services.booking_changes_service import change_booking
from backend.services.booking_service import create_booking
from backend.services.invoice_service import invoice as calculate,pay
from tests.backend.test_booking_consistency import data,concurrent


def test_shortening_below_paid_total_rolls_back_nights_segments_and_invoice(db):
    booking=create_booking(db,data())
    inv=calculate(booking.id,None,db);pay(inv.id,PaymentIn(amount=1700000),db)
    proposed=BookingChangeIn(room_id=1,check_in='2030-01-10',check_out='2030-01-11',reason='Khách muốn về sớm',expected_total=900000)
    with pytest.raises(HTTPException):change_booking(db,booking.id,proposed,1)
    db.refresh(booking);db.refresh(inv)
    assert booking.check_out.day==12 and inv.total==1800000 and inv.paid_amount==1700000
    assert db.scalar(select(func.count(BookingNight.id)))==2
    assert db.scalar(select(RoomStay.check_out)).day==12
    assert not db.scalar(select(BookingChange.id))


def test_two_reservations_cannot_move_into_same_target_room_concurrently(db):
    db.add_all([Room(id=2,number='303',floor=3,room_type_id=1),Room(id=3,number='304',floor=3,room_type_id=1)]);db.commit()
    first=create_booking(db,data())
    second=create_booking(db,BookingIn(customer_id=1,room_id=2,check_in='2030-01-10',check_out='2030-01-12',guests=2))
    ids=[first.id,second.id]
    proposed=BookingChangeIn(room_id=3,check_in='2030-01-10',check_out='2030-01-12',reason='Khách xin đổi phòng',expected_total=1800000)
    assert sorted(concurrent(lambda session,index:change_booking(session,ids[index],proposed,1)))==[200,409]
    assert db.scalar(select(func.count(RoomStay.id)).where(RoomStay.room_id==3))==1
