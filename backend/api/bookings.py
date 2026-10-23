from backend.dependencies import get_current_user, require_roles
from backend.services.booking_detail_service import booking_detail
from backend.services.booking_changes_service import change_booking
from backend.schemas.inputs import BookingChangeIn
from backend.schemas.outputs import BookingOut
from backend.models import Booking, BookingStatusHistory, Role
from backend.schemas import BookingIn
from backend.services.booking_service import booking_action as booking_action_service, bookings as bookings_service, create_booking
from core.database import get_db
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import select
from fastapi import HTTPException

router = APIRouter()


@router.post('/booking-changes/{booking_id}/preview')
def preview_change(booking_id: int, data: BookingChangeIn, db: Session = Depends(get_db), user=Depends(require_roles(Role.admin, Role.receptionist))):
    return change_booking(db, booking_id, data, user.id, preview=True)


@router.put('/bookings/{booking_id}')
def apply_change(booking_id: int, data: BookingChangeIn, db: Session = Depends(get_db), user=Depends(require_roles(Role.admin, Role.receptionist))):
    return change_booking(db, booking_id, data, user.id)

@router.get("/bookings",response_model=list[BookingOut])
def bookings(db: Session = Depends(get_db)):
    return bookings_service(db=db)


@router.post("/bookings",response_model=BookingOut)
def add_booking(data: BookingIn, db: Session = Depends(get_db), user=Depends(require_roles(Role.admin, Role.receptionist))):
    return create_booking(db, data, user.id)


@router.get('/bookings/{booking_id}')
def detail(booking_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    return booking_detail(db, booking_id, user.role.value)


@router.post('/bookings/{booking_id}/check-in')
def check_in(booking_id:int,db:Session=Depends(get_db),user=Depends(require_roles(Role.admin,Role.receptionist))):
    return booking_action_service(booking_id,'check-in',db,user.id)


@router.post('/bookings/{booking_id}/check-out')
def check_out(booking_id:int,db:Session=Depends(get_db),user=Depends(require_roles(Role.admin,Role.receptionist))):
    return booking_action_service(booking_id,'check-out',db,user.id)


@router.post('/bookings/{booking_id}/cancel')
def cancel(booking_id:int,db:Session=Depends(get_db),user=Depends(require_roles(Role.admin,Role.receptionist))):
    return booking_action_service(booking_id,'cancel',db,user.id)


@router.get("/bookings/{booking_id}/history")
def booking_history(booking_id: int, db: Session = Depends(get_db)):
    if not db.get(Booking, booking_id):
        raise HTTPException(404, "Không tìm thấy đặt phòng")
    return db.scalars(select(BookingStatusHistory).where(BookingStatusHistory.booking_id == booking_id).order_by(BookingStatusHistory.id)).all()
