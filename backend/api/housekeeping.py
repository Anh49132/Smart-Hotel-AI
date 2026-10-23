from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from core.database import get_db
from backend.dependencies import require_roles
from backend.models import Role
from backend.services.housekeeping_service import list_tasks, task_action

router=APIRouter()
allowed=require_roles(Role.admin,Role.receptionist,Role.housekeeping)


class TaskAction(BaseModel):
    action: str = Field(pattern='^(assign|start|complete|inspect)$')
    assigned_to: int | None = None


@router.get('/housekeeping')
def tasks(db: Session=Depends(get_db),user=Depends(allowed)):
    return list_tasks(db,user)


@router.post('/housekeeping/{task_id}')
def action(task_id:int,data:TaskAction,db:Session=Depends(get_db),user=Depends(allowed)):
    return task_action(db,task_id,data.action,user,data.assigned_to)
