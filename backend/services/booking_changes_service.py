from .money_service import net_received,charge_total
from .housekeeping_service import open_task, create_cleaning_task
import json
from decimal import Decimal, ROUND_HALF_UP
from fastapi import HTTPException
from sqlalchemy import select, delete
from backend.models import Booking, BookingNight, BookingChange, RoomStay, RoomStatus
from core.hotel_time import hotel_today
from .transactions import lock_room, write_transaction
from .rates_service import lock_room_type, quote, booked_room_amount
from .inventory_service import room_available
from .invoice_service import calculate_invoice


def proposed_change(db, booking, target, data):
    if booking.status.value not in ('confirmed', 'checked_in'):
        raise HTTPException(409, 'Chỉ thay đổi đặt phòng đang hiệu lực')
    if not target or target.status == RoomStatus.maintenance:
        raise HTTPException(409, 'Phòng đích không sẵn sàng')
    room_type = lock_room_type(db, target.room_type_id)
    if booking.guests > room_type.capacity:
        raise HTTPException(409, 'Phòng đích không đủ sức chứa')
    today = hotel_today()
    in_house = booking.status.value == 'checked_in'
    moving = target.id != booking.room_id
    if in_house and (data.check_in != booking.check_in or not booking.check_in <= today < data.check_out):
        raise HTTPException(409, 'Khách đang ở: giữ ngày nhận ban đầu, ngày trả phải sau hôm nay')
    if in_house and moving and (target.status != RoomStatus.available or open_task(db,target.id)):
        raise HTTPException(409, 'Phòng đích cần sẵn sàng để chuyển khách đang ở')
    cutoff = today if in_house and moving else min(booking.check_out, data.check_out) if in_house else data.check_in
    start = today if in_house else data.check_in
    if not room_available(db, target.id, start, data.check_out, booking.id):
        raise HTTPException(409, 'Phòng đích đã có lịch trùng')
    old_nights = db.scalars(select(BookingNight).where(BookingNight.booking_id == booking.id).order_by(BookingNight.stay_date)).all()
    if in_house and not old_nights:
        raise HTTPException(409, 'Lưu trú cũ chưa có giá từng đêm; cần đối chiếu trước khi thay đổi')
    retained = [{'stay_date':n.stay_date, 'amount':n.amount, 'source':n.source} for n in old_nights if in_house and n.stay_date < cutoff]
    added = quote(db, room_type, cutoff, data.check_out)['nights'] if cutoff < data.check_out else []
    nights = retained + added
    total = sum((n['amount'] for n in nights), Decimal(0))
    if total > Decimal('9999999999.99'):
        raise HTTPException(422, 'Tổng tiền phòng vượt giới hạn')
    return nights, total, today


def change_booking(db, booking_id, data, actor_id, preview=False):
    with write_transaction(db):
        current_room = db.scalar(select(Booking.room_id).where(Booking.id == booking_id))
        if current_room is None:
            raise HTTPException(404, 'Không tìm thấy đặt phòng')
        rooms = {room_id:lock_room(db, room_id) for room_id in sorted({current_room, data.room_id})}
        booking = db.scalar(select(Booking).where(Booking.id == booking_id).with_for_update().execution_options(populate_existing=True))
        if booking.room_id != current_room:
            raise HTTPException(409, 'Đặt phòng vừa được thay đổi, hãy tải lại')
        old_total = booked_room_amount(db, booking)
        nights, total, today = proposed_change(db, booking, rooms[data.room_id], data)
        result = {'old_room_total':str(old_total), 'new_room_total':str(total), 'difference':str(total-old_total), 'nights':[dict(n,stay_date=str(n['stay_date']),amount=str(n['amount'])) for n in nights]}
        if preview:
            db.rollback()
            return result
        if data.expected_total is None or data.expected_total != total:
            raise HTTPException(409, 'Cần xem và xác nhận lại báo giá mới trước khi thay đổi')
        before = {'room_id':booking.room_id,'check_in':str(booking.check_in),'check_out':str(booking.check_out),'room_total':str(old_total)}
        stays = db.scalars(select(RoomStay).where(RoomStay.booking_id == booking.id).order_by(RoomStay.check_in)).all()
        in_house = booking.status.value == 'checked_in'
        moving = current_room != data.room_id
        if not in_house:
            for stay in stays: db.delete(stay)
            db.add(RoomStay(booking_id=booking.id,room_id=data.room_id,check_in=data.check_in,check_out=data.check_out))
        elif moving:
            for stay in stays:
                if stay.check_in >= today: db.delete(stay)
                elif stay.check_out > today: stay.check_out=today
            db.add(RoomStay(booking_id=booking.id,room_id=data.room_id,check_in=today,check_out=data.check_out))
            rooms[current_room].status=RoomStatus.cleaning
            create_cleaning_task(db,current_room)
            rooms[data.room_id].status=RoomStatus.occupied
        else:
            current = next((s for s in reversed(stays) if s.room_id == current_room),None)
            if not current:
                raise HTTPException(409,'Thiếu chặng phân phòng, cần kiểm tra dữ liệu')
            current.check_out=data.check_out
        db.execute(delete(BookingNight).where(BookingNight.booking_id == booking.id))
        db.add_all([BookingNight(booking_id=booking.id,**n) for n in nights])
        booking.room_id=data.room_id
        booking.check_in, booking.check_out=data.check_in, data.check_out
        booking.booked_nightly_rate=(total/len(nights)).quantize(Decimal('.01'),rounding=ROUND_HALF_UP)
        booking.booked_rate_source='nightly_snapshot'
        db.flush()
        if booking.invoice is None and net_received(db,booking.id)>charge_total(db,booking):
            raise HTTPException(400,'Tổng mới thấp hơn số đã thu; cần xử lý hoàn/điều chỉnh trước')
        if booking.invoice is not None:
            calculate_invoice(db,booking,commit=False)
        after = {'room_id':data.room_id,'check_in':str(data.check_in),'check_out':str(data.check_out),'room_total':str(total)}
        db.add(BookingChange(booking_id=booking.id,changed_by=actor_id,reason=data.reason,before_data=json.dumps(before),after_data=json.dumps(after)))
        db.commit()
        return result
