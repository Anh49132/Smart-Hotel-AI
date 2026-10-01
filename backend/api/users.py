from backend.dependencies import require_roles
from backend.models import Role
from backend.schemas import UserCreate
from backend.services.users_service import add_user as add_user_service, list_users as list_users_service, toggle_user as toggle_user_service
from core.database import get_db
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

router = APIRouter()

@router.post("/users")
def add_user(data: UserCreate, db: Session = Depends(get_db), _=Depends(require_roles(Role.admin))):
    return add_user_service(data=data, db=db)


@router.get("/users")
def list_users(db: Session = Depends(get_db), _=Depends(require_roles(Role.admin))):
    return list_users_service(db=db)


@router.patch("/users/{user_id}/active")
def toggle_user(user_id: int, active: bool, db: Session = Depends(get_db), current=Depends(require_roles(Role.admin))):
    return toggle_user_service(user_id=user_id, active=active, db=db, current=current)
