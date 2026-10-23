from datetime import date
from fastapi import APIRouter,Depends
from pydantic import BaseModel,Field,model_validator
from sqlalchemy.orm import Session
from core.database import get_db
from backend.models import Role
from backend.dependencies import require_roles
from backend.services.maintenance_service import create_block,update_block,blocks

router=APIRouter()
allowed=require_roles(Role.admin,Role.receptionist)


class BlockIn(BaseModel):
    room_id:int
    start_date:date
    end_date:date
    description:str=Field(min_length=3,max_length=500)
    assigned_to:int|None=None

    @model_validator(mode='after')
    def dates(self):
        if self.end_date<=self.start_date: raise ValueError('Ngày kết thúc phải sau ngày bắt đầu')
        return self


class BlockStatus(BaseModel):
    status:str=Field(pattern='^(in_progress|resolved|cancelled)$')


@router.get('/maintenance')
def list_blocks(db:Session=Depends(get_db),user=Depends(allowed)):
    return blocks(db)


@router.post('/maintenance')
def add_block(data:BlockIn,db:Session=Depends(get_db),user=Depends(allowed)):
    return create_block(db,data,user)


@router.patch('/maintenance/{block_id}')
def edit_block(block_id:int,data:BlockStatus,db:Session=Depends(get_db),user=Depends(allowed)):
    return update_block(db,block_id,data.status,user)
