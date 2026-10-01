from backend.dependencies import require_roles
from backend.models import Role
from backend.schemas import BookingIn
from backend.services.booking_service import booking_action as booking_action_service, bookings as bookings_service, create_booking
from core.database import get_db
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

router = APIRouter()

@router.get("/bookings")
def bookings(db: Session = Depends(get_db)):
    return bookings_service(db=db)


@router.post("/bookings")
def add_booking(data: BookingIn, db: Session = Depends(get_db), _=Depends(require_roles(Role.admin, Role.receptionist))):
    return create_booking(db, data)


@router.post("/bookings/{booking_id}/{action}")
def booking_action(booking_id: int, action: str, db: Session = Depends(get_db), _=Depends(require_roles(Role.admin, Role.receptionist))):
    return booking_action_service(booking_id=booking_id, action=action, db=db)
