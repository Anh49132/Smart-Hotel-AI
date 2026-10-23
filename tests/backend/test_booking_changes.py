from datetime import date
from decimal import Decimal
from fastapi import HTTPException
from sqlalchemy import select
import pytest
from backend.models import Room, RoomStay, RoomType, BookingChange, BookingNight, Booking, RoomStatus
from backend.schemas import BookingIn
from backend.schemas.inputs import BookingChangeIn
from backend.services.booking_service import create_booking, booking_action, room_is_available
from backend.services.booking_changes_service import change_booking
from tests.backend.test_booking_consistency import data


def target(db):
    db.add(Room(id=2,number='303',floor=3,room_type_id=1)); db.commit()


def change(db, booking, room=2, start='2030-01-10', end='2030-01-13', apply=True):
    value=BookingChangeIn(room_id=room,check_in=start,check_out=end,reason='Khách yêu cầu')
    quoted=change_booking(db,booking.id,value,1,preview=True)
    if not apply: return quoted
    value.expected_total=Decimal(quoted['new_room_total'])
    return change_booking(db,booking.id,value,1)


def test_confirmed_change_and_failed_conflict_roll_back(db):
    target(db); booking=create_booking(db,data())
    change(db,booking)
    db.refresh(booking)
    assert booking.room_id==2 and booking.check_out==date(2030,1,13)
    assert len(db.scalars(select(BookingNight).where(BookingNight.booking_id==booking.id)).all())==3
    assert db.scalar(select(BookingChange.id))
    other=create_booking(db,data())
    with pytest.raises(HTTPException): change(db,booking,room=1)
    db.refresh(booking)
    assert booking.room_id==2
    assert room_is_available(db,1,date(2030,1,12),date(2030,1,13))


def test_inhouse_move_keeps_prior_nights_and_segments(db,monkeypatch):
    target(db); booking=create_booking(db,data())
    booking_action(booking.id,'check-in',db)
    monkeypatch.setattr('backend.services.booking_changes_service.hotel_today',lambda:date(2030,1,11))
    db.get(RoomType,1).nightly_rate=1000000; db.commit()
    result=change(db,booking)
    assert Decimal(result['new_room_total'])==2900000
    stays=db.scalars(select(RoomStay).where(RoomStay.booking_id==booking.id).order_by(RoomStay.check_in)).all()
    assert [(s.room_id,s.check_in.day,s.check_out.day) for s in stays]==[(1,10,11),(2,11,13)]
    assert db.get(Room,1).status==RoomStatus.cleaning and db.get(Room,2).status==RoomStatus.occupied
    assert not room_is_available(db,1,date(2030,1,10),date(2030,1,11))
    assert room_is_available(db,1,date(2030,1,11),date(2030,1,12))


def test_price_consent_rechecked_and_invalid_date_rejected(client,db):
    target(db); booking=create_booking(db,data())
    value={'room_id':2,'check_in':'2030-01-10','check_out':'2030-01-13','reason':'Đổi phòng','expected_total':'1'}
    assert client.put(f'/api/bookings/{booking.id}',json=value).status_code==409
    value['check_out']='2030-01-09'
    assert client.put(f'/api/bookings/{booking.id}',json=value).status_code==422
    assert client.get(f'/bookings/{booking.id}').status_code==200
