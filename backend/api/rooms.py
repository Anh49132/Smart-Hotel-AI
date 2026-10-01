from backend.dependencies import require_roles
from backend.models import Role, RoomStatus
from backend.schemas import RoomIn, RoomTypeIn
from backend.services.rooms_service import add_room as add_room_service, add_room_type as add_room_type_service, delete_room as delete_room_service, list_rooms as list_rooms_service, room_status as room_status_service, update_room as update_room_service
from core.database import get_db
from datetime import date
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Optional

router = APIRouter()

@router.get("/rooms")
def list_rooms(check_in: Optional[date] = None, check_out: Optional[date] = None, guests: int = 1, db: Session = Depends(get_db)):
    return list_rooms_service(check_in=check_in, check_out=check_out, guests=guests, db=db)


@router.post("/room-types")
def add_room_type(data: RoomTypeIn, db: Session = Depends(get_db), _=Depends(require_roles(Role.admin))):
    return add_room_type_service(data=data, db=db)


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
