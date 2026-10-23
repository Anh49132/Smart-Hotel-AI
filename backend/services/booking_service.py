from backend.models import Booking, BookingStatus, BookingStatusHistory, Customer, Room, RoomStatus
from backend.schemas import BookingIn
from backend.services.invoice_service import calculate_invoice
from datetime import date
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload
from typing import Optional
from uuid import uuid4
from .transactions import lock_room, write_transaction

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

def create_booking(db: Session, data: BookingIn, actor_id: int | None = None) -> Booking:
    with write_transaction(db):
        room = lock_room(db, data.room_id)
        if not db.get(Customer, data.customer_id):
            raise HTTPException(404, "Không tìm thấy khách hàng")
        if not room or room.status == RoomStatus.maintenance:
            raise HTTPException(400, "Phòng không tồn tại hoặc đang bảo trì")
        if data.guests > room.room_type.capacity:
            raise HTTPException(400, "Số khách vượt sức chứa của phòng")
        if not room_is_available(db, data.room_id, data.check_in, data.check_out):
            raise HTTPException(409, "Phòng đã có lịch trùng trong khoảng ngày này")
        booking = Booking(code=f"BK-{uuid4().hex[:8].upper()}", booked_nightly_rate=room.room_type.nightly_rate, **data.model_dump())
        db.add(booking)
        db.flush()
        db.add(BookingStatusHistory(booking_id=booking.id, to_status=BookingStatus.confirmed, changed_by=actor_id))
        db.commit()
        db.refresh(booking)
        return booking


def bookings(db: Session):
    return db.scalars(select(Booking).options(selectinload(Booking.customer), selectinload(Booking.room)).order_by(Booking.created_at.desc())).all()

def booking_action(booking_id: int, action: str, db: Session, actor_id: int | None = None):
    transitions = {'check-in': (BookingStatus.confirmed, BookingStatus.checked_in), 'check-out': (BookingStatus.checked_in, BookingStatus.checked_out), 'cancel': (BookingStatus.confirmed, BookingStatus.cancelled)}
    if action not in transitions:
        raise HTTPException(400, 'Thao tác không hợp lệ')
    with write_transaction(db):
        room_id = db.scalar(select(Booking.room_id).where(Booking.id == booking_id))
        if room_id is None:
            raise HTTPException(404, 'Không tìm thấy đặt phòng')
        room = lock_room(db, room_id)
        booking = db.scalar(select(Booking).where(Booking.id == booking_id).with_for_update().execution_options(populate_existing=True))
        expected, target = transitions[action]
        if booking.status != expected:
            raise HTTPException(409, 'Trạng thái đặt phòng không phù hợp')
        if action == 'cancel' and booking.invoice is not None:
            raise HTTPException(409, 'Đặt phòng đã có hóa đơn; cần xử lý điều chỉnh/hoàn tiền trước khi hủy')
        if action == 'check-in':
            other = db.scalar(select(Booking.id).where(Booking.room_id == room_id, Booking.status == BookingStatus.checked_in, Booking.id != booking_id).limit(1))
            if room.status != RoomStatus.available or other:
                raise HTTPException(409, 'Phòng chưa sẵn sàng nhận khách hoặc vẫn có khách đang lưu trú')
            room.status = RoomStatus.occupied
        elif action == 'check-out':
            room.status = RoomStatus.cleaning
        # Cancel changes reservations, not today's physical room state.
        db.add(BookingStatusHistory(booking_id=booking.id, from_status=expected, to_status=target, changed_by=actor_id))
        if action == 'check-out':
            calculate_invoice(db, booking, commit=False)
        booking.status = target
        db.commit()
        return {'ok': True, 'status': target}
