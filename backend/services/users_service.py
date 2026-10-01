from backend.models import User
from backend.schemas import UserCreate
from core.security import hash_password
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

def add_user(data: UserCreate, db: Session):
    item = User(username=data.username, full_name=data.full_name, role=data.role, password_hash=hash_password(data.password))
    db.add(item)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, 'Tên đăng nhập đã tồn tại')
    db.refresh(item)
    return {'id': item.id}

def list_users(db: Session):
    return [{'id': u.id, 'username': u.username, 'full_name': u.full_name, 'role': u.role.value, 'is_active': u.is_active} for u in db.scalars(select(User).order_by(User.full_name)).all()]

def toggle_user(user_id: int, active: bool, db: Session, current):
    item = db.get(User, user_id)
    if not item:
        raise HTTPException(404, 'Không tìm thấy tài khoản')
    if item.id == current.id and (not active):
        raise HTTPException(409, 'Không thể tự khóa tài khoản đang đăng nhập')
    item.is_active = active
    db.commit()
    return {'ok': True}
