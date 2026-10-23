from backend.dependencies import get_current_user, require_roles
from backend.schemas.inputs import PasswordIn, PasswordChange, UserRoleIn
from backend.services import users_service
from core.security import set_session_cookie
from backend.models import Role
from backend.schemas import UserCreate
from backend.services.users_service import add_user as add_user_service, list_users as list_users_service, toggle_user as toggle_user_service
from core.database import get_db
from fastapi import APIRouter, Depends, Response
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


@router.patch('/users/{user_id}/role')
def change_role(user_id: int, data: UserRoleIn, db: Session = Depends(get_db), current=Depends(require_roles(Role.admin))):
    return users_service.change_role(user_id, data.role, db, current)


@router.post('/users/{user_id}/password')
def reset_password(user_id: int, data: PasswordIn, db: Session = Depends(get_db), current=Depends(require_roles(Role.admin))):
    return users_service.reset_password(user_id, data.password, db, current)


@router.post('/account/password')
def change_password(data: PasswordChange, response: Response, db: Session = Depends(get_db), current=Depends(get_current_user)):
    user = users_service.change_password(current, data, db, current.token_version)
    set_session_cookie(response, user)
    return {'ok': True}
