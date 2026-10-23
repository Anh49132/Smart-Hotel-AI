from datetime import timedelta
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from fastapi import HTTPException
from backend.models import Booking, Room, RoomStay, RoomType


def room_calendar(db, start, end, guests=1, type_id=None, floor=None, page=1):
    if not 1 <= (end-start).days <= 31:
        raise HTTPException(422, 'Lịch hiển thị từ 1 đến 31 ngày')
    query=select(Room).join(RoomType).options(selectinload(Room.room_type)).where(RoomType.capacity>=guests)
    if type_id is not None: query=query.where(Room.room_type_id==type_id)
    if floor is not None: query=query.where(Room.floor==floor)
    total=db.scalar(select(func.count()).select_from(query.subquery()))
    rooms=db.scalars(query.order_by(Room.floor,Room.number).offset((page-1)*20).limit(20)).all()
    ids=[r.id for r in rooms]
    segments=db.execute(select(RoomStay,Booking).join(Booking,Booking.id==RoomStay.booking_id).where(RoomStay.room_id.in_(ids),RoomStay.check_in<end,RoomStay.check_out>start,Booking.status.in_(('confirmed','checked_in','checked_out')))).all()
    # Compatibility for imported records without segments; normal writes always create them.
    legacy=db.scalars(select(Booking).where(Booking.room_id.in_(ids),Booking.check_in<end,Booking.check_out>start,Booking.status.in_(('confirmed','checked_in','checked_out')),~select(RoomStay.id).where(RoomStay.booking_id==Booking.id).exists())).all()
    spans=[(s.room_id,s.check_in,s.check_out,b) for s,b in segments]+[(b.room_id,b.check_in,b.check_out,b) for b in legacy]
    days=[start+timedelta(days=i) for i in range((end-start).days)]
    rows=[]
    for room in rooms:
        cells=[]
        for day in days:
            items=[{'id':b.id,'code':b.code,'status':b.status.value} for room_id,ci,co,b in spans if room_id==room.id and ci<=day<co]
            cells.append({'date':str(day),'next_date':str(day+timedelta(days=1)),'bookings':items,
                          'can_book':not any(b['status'] in ('confirmed','checked_in') for b in items) and room.room_type.is_active and room.status.value!='maintenance'})
        rows.append({'id':room.id,'number':room.number,'floor':room.floor,'type':room.room_type.name,'status':room.status.value,'cells':cells})
    return {'start':str(start),'end':str(end),'days':[str(d) for d in days],'rooms':rows,'total':total,'page':page,'pages':max(1,(total+19)//20)}
