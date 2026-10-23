from concurrent.futures import ThreadPoolExecutor
from datetime import date
from threading import Barrier
import pytest
from fastapi import HTTPException
from sqlalchemy import func, select
from backend.models import Booking, BookingStatus, BookingStatusHistory, Room, RoomStatus
from backend.schemas import BookingIn
from backend.services.booking_service import booking_action, create_booking
from core.database import SessionLocal


def data(day=10):
    return BookingIn(customer_id=1,room_id=1,check_in=date(2030,1,day),check_out=date(2030,1,day+2),guests=2)


def test_cancel_and_rebook_identical_dates(db):
    first = create_booking(db, data())
    booking_action(first.id, 'cancel', db)
    second = create_booking(db, data())
    assert first.id != second.id


def test_cancel_future_keeps_occupied_room(db):
    first = create_booking(db,data())
    future = create_booking(db,data(20))
    booking_action(first.id,'check-in',db)
    booking_action(future.id,'cancel',db)
    assert db.get(Room,1).status == RoomStatus.occupied


@pytest.mark.parametrize('status',[RoomStatus.cleaning,RoomStatus.maintenance,RoomStatus.occupied])
def test_checkin_requires_ready_room(db,status):
    booking = create_booking(db,data())
    db.get(Room,1).status=status
    db.commit()
    with pytest.raises(HTTPException) as error:
        booking_action(booking.id,'check-in',db)
    assert error.value.status_code == 409
    assert db.get(Booking,booking.id).status == BookingStatus.confirmed


def test_adjacent_dates_allowed(db):
    create_booking(db,data())
    create_booking(db,data(12))


def test_cannot_free_occupied_room_from_status_endpoint(client):
    booking=client.post('/api/bookings',json=data().model_dump(mode='json')).json()
    assert client.post(f"/api/bookings/{booking['id']}/check-in").status_code == 200
    assert client.patch('/api/rooms/1/status?status=available').status_code == 409


def concurrent(work):
    barrier=Barrier(2)
    def run(index):
        with SessionLocal() as session:
            barrier.wait(timeout=10)
            try:
                work(session,index)
                return 200
            except HTTPException as error:
                return error.status_code
    with ThreadPoolExecutor(max_workers=2) as executor:
        return list(executor.map(run,[0,1]))


def test_concurrent_overlap_only_one_created(db):
    results=concurrent(lambda session,index:create_booking(session,data(10+index)))
    assert sorted(results) == [200,409]
    assert db.scalar(select(func.count(Booking.id))) == 1


def test_concurrent_checkin_only_one_transition(db):
    booking=create_booking(db,data())
    results=concurrent(lambda session,index:booking_action(booking.id,'check-in',session))
    assert sorted(results) == [200,409]
    assert db.scalar(select(func.count(BookingStatusHistory.id)).where(BookingStatusHistory.to_status == BookingStatus.checked_in)) == 1


def test_checkout_and_service_are_serialized(db):
    from backend.models import Invoice, ServiceUsage
    from backend.schemas import ServiceUsageIn
    from backend.services.services_service import use_service
    booking=create_booking(db,data())
    booking_action(booking.id,'check-in',db)
    booking_id=booking.id  # Pass a scalar, never a session-bound ORM object across threads.
    def work(session,index):
        if index == 0:
            booking_action(booking_id,'check-out',session)
        else:
            use_service(ServiceUsageIn(booking_id=booking_id,service_id=1,quantity=2),session)
    results=concurrent(work)
    assert results[0] == 200
    assert results[1] in (200,409)
    invoice=db.scalar(select(Invoice).where(Invoice.booking_id==booking.id))
    expected=db.scalar(select(func.coalesce(func.sum(ServiceUsage.unit_price*ServiceUsage.quantity),0)).where(ServiceUsage.booking_id==booking.id))
    assert invoice.service_amount == expected
