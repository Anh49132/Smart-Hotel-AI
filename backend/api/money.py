from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select
from backend.dependencies import require_roles
from backend.models import Role,Booking,MoneyEntry
from backend.schemas.inputs import ReceiptIn
from backend.services.money_service import receipt,serialized_balance
from core.database import get_db

router=APIRouter()
cashiers=require_roles(Role.admin,Role.receptionist,Role.accountant)


@router.post('/bookings/{booking_id}/receipts')
def add_receipt(booking_id:int,data:ReceiptIn,db:Session=Depends(get_db),user=Depends(cashiers)):
    if user.role==Role.receptionist and data.kind!='deposit':raise HTTPException(403,'Lễ tân chỉ ghi nhận cọc trước nhận phòng')
    return receipt(db,booking_id,data,user.id)


@router.get('/bookings/{booking_id}/balance')
def booking_balance(booking_id:int,db:Session=Depends(get_db),user=Depends(cashiers)):
    booking=db.get(Booking,booking_id)
    if not booking:raise HTTPException(404,'Không tìm thấy đặt phòng')
    return serialized_balance(db,booking)


@router.get('/bookings/{booking_id}/receipts')
def receipts(booking_id:int,db:Session=Depends(get_db),user=Depends(require_roles(Role.admin,Role.accountant))):
    if not db.get(Booking,booking_id):raise HTTPException(404,'Không tìm thấy đặt phòng')
    return [{'id':e.id,'amount':str(e.amount),'kind':e.kind,'method':e.method,'reference':e.reference,'actor_id':e.actor_id,'at':e.occurred_at.isoformat()} for e in db.scalars(select(MoneyEntry).where(MoneyEntry.booking_id==booking_id).order_by(MoneyEntry.id))]
