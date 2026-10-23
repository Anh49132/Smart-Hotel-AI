from decimal import Decimal
from typing import Literal
from fastapi import APIRouter,Depends
from pydantic import BaseModel,Field
from sqlalchemy.orm import Session
from backend.dependencies import require_roles
from backend.models import Role
from backend.schemas.inputs import ReceiptIn,PaymentIn
from backend.services.refunds_service import refund,settle_cancellation,cancellation_policy,save_cancellation_policy
from core.database import get_db

router=APIRouter()
finance=require_roles(Role.admin,Role.accountant)


class CancellationIn(BaseModel):
    target_status:Literal['cancelled','no_show']='cancelled'
    reason:str=Field(min_length=3,max_length=500)
    request_key:str=Field(min_length=8,max_length=64,pattern=r'^[A-Za-z0-9_-]+$')
    expected_fee:Decimal|None=Field(default=None,ge=0,max_digits=12,decimal_places=2)


class RefundIn(PaymentIn):
    request_key:str=Field(min_length=8,max_length=64,pattern=r'^[A-Za-z0-9_-]+$')
    reason:str=Field(min_length=3,max_length=500)


class CancellationPolicyIn(BaseModel):
    cancellation_percent:Decimal=Field(ge=0,le=100,max_digits=5,decimal_places=2)
    no_show_percent:Decimal=Field(ge=0,le=100,max_digits=5,decimal_places=2)


@router.get('/finance/policy')
def get_policy(db:Session=Depends(get_db),user=Depends(finance)):return cancellation_policy(db)


@router.put('/finance/policy')
def set_policy(data:CancellationPolicyIn,db:Session=Depends(get_db),user=Depends(require_roles(Role.admin))):return save_cancellation_policy(db,data)


@router.post('/finance/{booking_id}/cancellation-preview')
def preview(booking_id:int,data:CancellationIn,db:Session=Depends(get_db),user=Depends(finance)):return settle_cancellation(db,booking_id,data,user,True)


@router.post('/finance/{booking_id}/cancellation')
def cancel(booking_id:int,data:CancellationIn,db:Session=Depends(get_db),user=Depends(finance)):return settle_cancellation(db,booking_id,data,user)


@router.post('/finance/{booking_id}/refunds')
def give_refund(booking_id:int,data:RefundIn,db:Session=Depends(get_db),user=Depends(finance)):return refund(db,booking_id,data,user)
