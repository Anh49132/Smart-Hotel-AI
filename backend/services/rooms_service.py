from backend.models import Booking, BookingStatus, Room, RoomStatus, RoomType
from backend.schemas import RoomIn, RoomTypeIn
from datetime import date
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload
from typing import Optional
from .transactions import lock_room, write_transaction


def validate_physical_status(db, room_id, status):
    checked_in = db.scalar(select(Booking.id).where(Booking.room_id == room_id, Booking.status == BookingStatus.checked_in).limit(1))
    if checked_in and status != RoomStatus.occupied:
        raise HTTPException(409, 'Phòng vẫn có khách, hãy thực hiện trả phòng trước')
    if not checked_in and status == RoomStatus.occupied:
        raise HTTPException(409, 'Dùng thao tác nhận phòng để chuyển sang đang ở')

def list_rooms(check_in: Optional[date], check_out: Optional[date], guests: int, db: Session):
    query = select(Room).options(selectinload(Room.room_type)).join(RoomType).order_by(Room.number)
    if check_in and check_out:
        if check_out <= check_in:
            raise HTTPException(422, 'Ngày trả phải sau ngày nhận')
        blocked = select(Booking.room_id).where(Booking.status.in_((BookingStatus.confirmed, BookingStatus.checked_in)), Booking.check_in < check_out, check_in < Booking.check_out)
        query = query.where(Room.id.not_in(blocked), Room.status != RoomStatus.maintenance, RoomType.capacity >= guests)
    rooms = db.scalars(query).all()
    return [{'id': r.id, 'number': r.number, 'floor': r.floor, 'status': r.status.value, 'room_type': {'id': r.room_type.id, 'name': r.room_type.name, 'capacity': r.room_type.capacity, 'nightly_rate': float(r.room_type.nightly_rate)}} for r in rooms]

def add_room_type(data: RoomTypeIn, db: Session):
    item = RoomType(**data.model_dump())
    db.add(item)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, 'Tên loại phòng đã tồn tại')
    db.refresh(item)
    return item

def add_room(data: RoomIn, db: Session):
    if not db.get(RoomType, data.room_type_id):
        raise HTTPException(404, 'Không tìm thấy loại phòng')
    item = Room(**data.model_dump())
    db.add(item)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, 'Số phòng đã tồn tại')
    db.refresh(item)
    return item

def update_room(room_id: int, data: RoomIn, db: Session):
    with write_transaction(db):
        room = lock_room(db, room_id)
        if not room:
            raise HTTPException(404, 'Không tìm thấy phòng')
        room_type = db.get(RoomType, data.room_type_id)
        if not room_type:
            raise HTTPException(404, 'Không tìm thấy loại phòng')
        validate_physical_status(db, room_id, data.status)
        oversized = db.scalar(select(Booking.id).where(Booking.room_id == room_id, Booking.status.in_((BookingStatus.confirmed, BookingStatus.checked_in)), Booking.guests > room_type.capacity).limit(1))
        if oversized:
            raise HTTPException(409, 'Loại phòng mới không đủ sức chứa cho đặt phòng hiện có')
        for key, value in data.model_dump().items():
            setattr(room, key, value)
        db.commit()
    return {'ok': True}

def delete_room(room_id: int, db: Session):
    room = db.get(Room, room_id)
    if not room:
        raise HTTPException(404, 'Không tìm thấy phòng')
    if db.scalar(select(Booking.id).where(Booking.room_id == room_id).limit(1)):
        raise HTTPException(409, 'Phòng đã có lịch sử đặt, không thể xóa')
    db.delete(room)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, 'Phòng đã có lịch sử đặt, không thể xóa')
    return {'ok': True}

def room_status(room_id: int, status: RoomStatus, db: Session):
    with write_transaction(db):
        room = lock_room(db, room_id)
        if not room:
            raise HTTPException(404, 'Không tìm thấy phòng')
        validate_physical_status(db, room_id, status)
        room.status = status
        db.commit()
    return {'ok': True}
