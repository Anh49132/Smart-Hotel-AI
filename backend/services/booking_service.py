from backend.models import Booking, BookingStatus, Room, RoomStatus
from backend.schemas import BookingIn
from backend.services.invoice_service import calculate_invoice
from datetime import date
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload
from typing import Optional
from uuid import uuid4

ACTIVE_BOOKING_STATUSES = (BookingStatus.confirmed, BookingStatus.checked_in)

def room_is_available(db: Session, room_id: int, check_in: date, check_out: date, exclude_id: Optional[int] = None) -> bool:
    query = select(Booking.id).where(
        Booking.room_id == room_id,
        Booking.status.in_(ACTIVE_BOOKING_STATUSES),
        Booking.check_in < check_out,
        check_in < Booking.check_out,
    )
    if exclude_id:
        query = query.where(Booking.id != exclude_id)
    return db.scalar(query.limit(1)) is None

def create_booking(db: Session, data: BookingIn) -> Booking:
    room = db.execute(select(Room).where(Room.id == data.room_id).with_for_update()).scalar_one_or_none()
    if not room or room.status == RoomStatus.maintenance:
        raise HTTPException(400, "Phòng không tồn tại hoặc đang bảo trì")
    if data.guests > room.room_type.capacity:
        raise HTTPException(400, "Số khách vượt sức chứa của phòng")
    if not room_is_available(db, data.room_id, data.check_in, data.check_out):
        raise HTTPException(409, "Phòng đã có lịch trùng trong khoảng ngày này")
    booking = Booking(code=f"BK-{uuid4().hex[:8].upper()}", **data.model_dump())
    db.add(booking)
    db.commit()
    db.refresh(booking)
    return booking


def bookings(db: Session):
    return db.scalars(select(Booking).options(selectinload(Booking.customer), selectinload(Booking.room)).order_by(Booking.created_at.desc())).all()

def booking_action(booking_id: int, action: str, db: Session):
    booking = db.get(Booking, booking_id)
    if not booking:
        raise HTTPException(404, 'Không tìm thấy đặt phòng')
    transitions = {'check-in': (BookingStatus.confirmed, BookingStatus.checked_in, RoomStatus.occupied), 'check-out': (BookingStatus.checked_in, BookingStatus.checked_out, RoomStatus.cleaning), 'cancel': (BookingStatus.confirmed, BookingStatus.cancelled, RoomStatus.available)}
    if action not in transitions:
        raise HTTPException(400, 'Thao tác không hợp lệ')
    expected, target, room_status = transitions[action]
    if booking.status != expected:
        raise HTTPException(409, 'Trạng thái đặt phòng không phù hợp')
    booking.status, booking.room.status = (target, room_status)
    db.commit()
    if action == 'check-out':
        calculate_invoice(db, booking)
    return {'ok': True, 'status': target}
