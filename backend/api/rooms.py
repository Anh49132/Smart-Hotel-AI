from backend.dependencies import require_roles
from backend.models import Role, RoomStatus, RoomType, RatePlan
from backend.schemas.inputs import RatePlanIn
from backend.services import rates_service
from sqlalchemy import select
from backend.schemas import RoomIn, RoomTypeIn
from backend.services.rooms_service import add_room as add_room_service, add_room_type as add_room_type_service, delete_room as delete_room_service, list_rooms as list_rooms_service, room_status as room_status_service, update_room as update_room_service
from core.database import get_db
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional

router = APIRouter()

@router.get("/rooms")
def list_rooms(check_in: Optional[date] = None, check_out: Optional[date] = None, guests: int = Query(default=1, ge=1, le=20), db: Session = Depends(get_db)):
    if (check_in is None) != (check_out is None):
        raise HTTPException(422, 'Cần cả ngày nhận và ngày trả')
    return list_rooms_service(check_in=check_in, check_out=check_out, guests=guests, db=db)


@router.post("/room-types")
def add_room_type(data: RoomTypeIn, db: Session = Depends(get_db), _=Depends(require_roles(Role.admin))):
    return add_room_type_service(data=data, db=db)


@router.get('/room-types')
def room_types(db: Session = Depends(get_db)):
    return db.scalars(select(RoomType).order_by(RoomType.name)).all()


@router.put('/room-types/{type_id}')
def update_room_type(type_id: int, data: RoomTypeIn, db: Session = Depends(get_db), _=Depends(require_roles(Role.admin))):
    return rates_service.update_room_type(db, type_id, data)


@router.delete('/room-types/{type_id}')
def delete_room_type(type_id: int, db: Session = Depends(get_db), _=Depends(require_roles(Role.admin))):
    return rates_service.delete_room_type(db, type_id)


@router.get('/room-types/{type_id}/quote')
def rate_quote(type_id: int, check_in: date, check_out: date, db: Session = Depends(get_db)):
    item = db.get(RoomType, type_id)
    if not item:
        raise HTTPException(404, 'Không tìm thấy loại phòng')
    return rates_service.quote(db, item, check_in, check_out)


@router.get('/room-types/{type_id}/rate-plans')
def rate_plans(type_id: int, db: Session = Depends(get_db)):
    if not db.get(RoomType, type_id):
        raise HTTPException(404, 'Không tìm thấy loại phòng')
    return db.scalars(select(RatePlan).where(RatePlan.room_type_id == type_id).order_by(RatePlan.start_date)).all()


@router.post('/room-types/{type_id}/rate-plans')
def add_rate_plan(type_id: int, data: RatePlanIn, db: Session = Depends(get_db), _=Depends(require_roles(Role.admin))):
    return rates_service.save_rate_plan(db, type_id, data)


@router.put('/room-types/{type_id}/rate-plans/{plan_id}')
def update_rate_plan(type_id: int, plan_id: int, data: RatePlanIn, db: Session = Depends(get_db), _=Depends(require_roles(Role.admin))):
    return rates_service.save_rate_plan(db, type_id, data, plan_id)


@router.post("/rooms")
def add_room(data: RoomIn, db: Session = Depends(get_db), _=Depends(require_roles(Role.admin, Role.receptionist))):
    return add_room_service(data=data, db=db)


@router.put("/rooms/{room_id}")
def update_room(room_id: int, data: RoomIn, db: Session = Depends(get_db), _=Depends(require_roles(Role.admin, Role.receptionist))):
    return update_room_service(room_id=room_id, data=data, db=db)


@router.delete("/rooms/{room_id}")
def delete_room(room_id: int, db: Session = Depends(get_db), _=Depends(require_roles(Role.admin))):
    return delete_room_service(room_id=room_id, db=db)


@router.patch("/rooms/{room_id}/status")
def room_status(room_id: int, status: RoomStatus, db: Session = Depends(get_db), _=Depends(require_roles(Role.admin, Role.receptionist))):
    return room_status_service(room_id=room_id, status=status, db=db)
