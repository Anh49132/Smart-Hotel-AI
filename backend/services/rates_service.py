"""Price resolution shared by booking, availability, AI and invoices."""
from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP
from fastapi import HTTPException
from sqlalchemy import select, update
from backend.models import Booking, BookingNight, BookingStatus, RatePlan, Room, RoomType
from .transactions import write_transaction


def lock_room_type(db, type_id):
    if db.get_bind().dialect.name == 'sqlite':
        db.execute(update(RoomType).where(RoomType.id == type_id).values(id=RoomType.id).execution_options(synchronize_session=False))
    item = db.scalar(select(RoomType).where(RoomType.id == type_id).with_for_update().execution_options(populate_existing=True))
    if not item:
        raise HTTPException(404, 'Không tìm thấy loại phòng')
    return item


def quote(db, room_type, check_in, check_out):
    count = (check_out - check_in).days
    if count < 1 or count > 365:
        raise HTTPException(422, 'Khoảng lưu trú phải từ 1 đến 365 đêm')
    if not room_type.is_active:
        raise HTTPException(409, 'Loại phòng đã ngừng bán')
    plans = db.scalars(select(RatePlan).where(RatePlan.room_type_id == room_type.id, RatePlan.is_active.is_(True), RatePlan.start_date < check_out, RatePlan.end_date > check_in).order_by(RatePlan.start_date, RatePlan.id)).all()
    nights = []
    for offset in range(count):
        day = check_in + timedelta(days=offset)
        applicable = [p for p in plans if p.start_date <= day < p.end_date]
        if len(applicable) > 1:
            raise HTTPException(409, 'Bảng giá đặc biệt trùng lịch, cần quản trị viên điều chỉnh')
        if applicable:
            amount, source = applicable[0].nightly_rate, applicable[0].name
        elif day.weekday() in (5, 6) and room_type.weekend_rate is not None:
            amount, source = room_type.weekend_rate, 'Cuối tuần'
        else:
            amount, source = room_type.nightly_rate, 'Giá thường'
        nights.append({'stay_date': day, 'amount': amount, 'source': source})
    total = sum((n['amount'] for n in nights), Decimal('0'))
    if total > Decimal('9999999999.99'):
        raise HTTPException(422, 'Tổng tiền phòng vượt giới hạn hóa đơn của hệ thống')
    return {'nights': nights, 'total': total, 'average': (total / count).quantize(Decimal('.01'), rounding=ROUND_HALF_UP)}


def booked_room_amount(db, booking):
    nights = db.scalars(select(BookingNight).where(BookingNight.booking_id == booking.id).order_by(BookingNight.stay_date)).all()
    if not nights:
        if booking.booked_rate_source == 'nightly_snapshot':
            raise HTTPException(409, 'Thiếu chi tiết giá đã chốt theo đêm')
        return booking.booked_nightly_rate * (booking.check_out - booking.check_in).days
    count = (booking.check_out - booking.check_in).days
    if len(nights) != count or any(n.stay_date != booking.check_in + timedelta(days=i) for i, n in enumerate(nights)):
        raise HTTPException(409, 'Chi tiết giá theo đêm không khớp ngày lưu trú')
    return sum((night.amount for night in nights), Decimal('0'))


def update_room_type(db, type_id, data):
    with write_transaction(db):
        item = lock_room_type(db, type_id)
        too_large = db.scalar(select(Booking.id).join(Room, Room.id == Booking.room_id).where(Room.room_type_id == type_id, Booking.status.in_((BookingStatus.confirmed, BookingStatus.checked_in)), Booking.guests > data.capacity).limit(1))
        if too_large:
            raise HTTPException(409, 'Sức chứa mới không đủ cho đặt phòng đang hiệu lực')
        for key, value in data.model_dump().items():
            setattr(item, key, value)
        db.commit()
    return {'ok': True}


def save_rate_plan(db, type_id, data, plan_id=None):
    with write_transaction(db):
        lock_room_type(db, type_id)
        item = db.get(RatePlan, plan_id) if plan_id else RatePlan(room_type_id=type_id)
        if item is None or item.room_type_id != type_id:
            raise HTTPException(404, 'Không tìm thấy bảng giá')
        if data.is_active:
            overlap = select(RatePlan.id).where(RatePlan.room_type_id == type_id, RatePlan.is_active.is_(True), RatePlan.start_date < data.end_date, RatePlan.end_date > data.start_date)
            if plan_id:
                overlap = overlap.where(RatePlan.id != plan_id)
            if db.scalar(overlap.limit(1)):
                raise HTTPException(409, 'Khoảng giá đặc biệt trùng bảng giá đang áp dụng')
        for key, value in data.model_dump().items():
            setattr(item, key, value)
        db.add(item)
        db.commit()
        db.refresh(item)
        return item


def delete_room_type(db, type_id):
    with write_transaction(db):
        item = lock_room_type(db, type_id)
        if db.scalar(select(Room.id).where(Room.room_type_id == type_id).limit(1)) or db.scalar(select(RatePlan.id).where(RatePlan.room_type_id == type_id).limit(1)):
            raise HTTPException(409, 'Loại phòng đã được sử dụng; hãy chọn ngừng bán để giữ lịch sử')
        db.delete(item)
        db.commit()
    return {'ok': True}
