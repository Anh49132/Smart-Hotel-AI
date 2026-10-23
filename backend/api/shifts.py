from decimal import Decimal
from fastapi import APIRouter,Depends
from pydantic import BaseModel,Field
from sqlalchemy import select
from backend.dependencies import require_roles
from backend.models import Role,CashierShift
from core.database import get_db
from backend.services.shifts_service import open_shift,close_shift,shift_view

router=APIRouter(prefix='/shifts')
cashiers=require_roles(Role.admin,Role.accountant,Role.receptionist)

class OpenShiftIn(BaseModel):
    opening_cash:Decimal=Field(ge=0,le=9999999999,max_digits=12,decimal_places=2)

class CloseShiftIn(BaseModel):
    counted_cash:Decimal=Field(ge=0,le=9999999999,max_digits=12,decimal_places=2)
    handed_to:int|None=None
    note:str=Field(min_length=3,max_length=2000)

@router.get('')
def history(db=Depends(get_db),user=Depends(cashiers)):
    query=select(CashierShift).order_by(CashierShift.id.desc()).limit(100)
    if user.role!=Role.admin:query=query.where(CashierShift.cashier_id==user.id)
    return [shift_view(db,item) for item in db.scalars(query)]

@router.post('')
def open_cashier_shift(data:OpenShiftIn,db=Depends(get_db),user=Depends(cashiers)):
    return open_shift(db,user,data.opening_cash)

@router.post('/{shift_id}/close')
def close_cashier_shift(shift_id:int,data:CloseShiftIn,db=Depends(get_db),user=Depends(cashiers)):
    return close_shift(db,shift_id,user,data)
