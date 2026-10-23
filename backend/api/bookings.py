from backend.dependencies import require_roles
from backend.models import Booking, BookingStatusHistory, Role
from backend.schemas import BookingIn
from backend.services.booking_service import booking_action as booking_action_service, bookings as bookings_service, create_booking
from core.database import get_db
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import select
from fastapi import HTTPException

router = APIRouter()

@router.get("/bookings")
def bookings(db: Session = Depends(get_db)):
    return bookings_service(db=db)


@router.post("/bookings")
def add_booking(data: BookingIn, db: Session = Depends(get_db), user=Depends(require_roles(Role.admin, Role.receptionist))):
    return create_booking(db, data, user.id)


@router.post("/bookings/{booking_id}/{action}")
def booking_action(booking_id: int, action: str, db: Session = Depends(get_db), user=Depends(require_roles(Role.admin, Role.receptionist))):
    return booking_action_service(booking_id=booking_id, action=action, db=db, actor_id=user.id)


@router.get("/bookings/{booking_id}/history")
def booking_history(booking_id: int, db: Session = Depends(get_db)):
    if not db.get(Booking, booking_id):
        raise HTTPException(404, "Không tìm thấy đặt phòng")
    return db.scalars(select(BookingStatusHistory).where(BookingStatusHistory.booking_id == booking_id).order_by(BookingStatusHistory.id)).all()
