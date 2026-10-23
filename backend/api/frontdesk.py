from decimal import Decimal
from pydantic import BaseModel,Field,model_validator
from fastapi import APIRouter,Depends
from sqlalchemy.orm import Session
from backend.dependencies import require_roles
from backend.models import Role
from core.database import get_db
from backend.services.frontdesk_service import desk_rows,save_policy,mark_no_show,confirm_fee
from typing import Literal

router=APIRouter()
desk=require_roles(Role.admin,Role.receptionist)


class PolicyIn(BaseModel):
    check_in_hour:int=Field(ge=0,le=23)
    check_out_hour:int=Field(ge=0,le=23)
    no_show_hour:int=Field(ge=0,le=23)
    early_fee:Decimal=Field(ge=0,max_digits=12,decimal_places=2)
    late_fee:Decimal=Field(ge=0,max_digits=12,decimal_places=2)

    @model_validator(mode='after')
    def timing(self):
        if self.no_show_hour<self.check_in_hour:
            raise ValueError('Giờ no-show không được sớm hơn giờ nhận phòng')
        return self


class FeeIn(BaseModel):
    kind:Literal['early','late']
    expected_amount:Decimal=Field(gt=0,max_digits=12,decimal_places=2)


@router.get('/frontdesk')
def list_desk(db:Session=Depends(get_db),user=Depends(desk)):
    return desk_rows(db)


@router.put('/frontdesk/policy')
def update_policy(data:PolicyIn,db:Session=Depends(get_db),user=Depends(require_roles(Role.admin))):
    return save_policy(db,data)


@router.post('/frontdesk/{booking_id}/no-show')
def no_show(booking_id:int,db:Session=Depends(get_db),user=Depends(desk)):
    return mark_no_show(db,booking_id,user)


@router.post('/frontdesk/{booking_id}/surcharges')
def surcharge(booking_id:int,data:FeeIn,db:Session=Depends(get_db),user=Depends(desk)):
    return confirm_fee(db,booking_id,data,user)
