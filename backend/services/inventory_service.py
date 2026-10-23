"""Half-open room allocation intervals, including historical room moves."""
from sqlalchemy import select, union
from backend.models import Booking, BookingStatus, RoomStay, RoomBlock

ACTIVE = (BookingStatus.confirmed, BookingStatus.checked_in)


def blocked_rooms(check_in, check_out, exclude_id=None):
    segments = select(RoomStay.room_id).join(Booking, Booking.id == RoomStay.booking_id).where(
        Booking.status.in_(ACTIVE), RoomStay.check_in < check_out, RoomStay.check_out > check_in)
    legacy = select(Booking.room_id).where(Booking.status.in_(ACTIVE), Booking.check_in < check_out,
        Booking.check_out > check_in, ~select(RoomStay.id).where(RoomStay.booking_id == Booking.id).exists())
    if exclude_id:
        segments = segments.where(Booking.id != exclude_id)
        legacy = legacy.where(Booking.id != exclude_id)
    maintenance=select(RoomBlock.room_id).where(RoomBlock.status.in_(('open','in_progress')),RoomBlock.start_date<check_out,RoomBlock.end_date>check_in)
    return union(segments, legacy, maintenance)


def maintenance_blocks(db,room_id,start,end):
    return db.scalar(select(RoomBlock.id).where(RoomBlock.room_id==room_id,RoomBlock.status.in_(('open','in_progress')),RoomBlock.start_date<end,RoomBlock.end_date>start).limit(1)) is not None


def room_available(db, room_id, check_in, check_out, exclude_id=None):
    blocked = blocked_rooms(check_in, check_out, exclude_id).subquery()
    return db.scalar(select(blocked.c.room_id).where(blocked.c.room_id == room_id).limit(1)) is None
