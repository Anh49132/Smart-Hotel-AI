from backend.models import User
from backend.schemas import UserCreate
from core.security import hash_password, verify_password
from fastapi import HTTPException
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

def add_user(data: UserCreate, db: Session):
    item = User(username=data.username, full_name=data.full_name, role=data.role, password_hash=hash_password(data.password), must_change_password=True)
    db.add(item)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, 'Tên đăng nhập đã tồn tại')
    db.refresh(item)
    return {'id': item.id}

def list_users(db: Session):
    return [{'id': u.id, 'username': u.username, 'full_name': u.full_name, 'role': u.role.value, 'is_active': u.is_active, 'must_change_password': u.must_change_password} for u in db.scalars(select(User).order_by(User.full_name)).all()]

def locked_user(db, user_id):
    # Serialize account mutations before loading the latest session version.
    if db.bind.dialect.name == 'sqlite':
        db.execute(update(User).where(User.id == user_id).values(id=user_id).execution_options(synchronize_session=False))
    item = db.scalar(select(User).where(User.id == user_id).with_for_update().execution_options(populate_existing=True))
    if not item:
        raise HTTPException(404, 'Không tìm thấy tài khoản')
    return item


def toggle_user(user_id: int, active: bool, db: Session, current):
    item = locked_user(db, user_id)
    if item.id == current.id and not active:
        raise HTTPException(409, 'Không thể tự khóa tài khoản đang đăng nhập')
    if item.is_active != active:
        item.is_active = active
        item.token_version += 1
    db.commit()
    return {'ok': True}


def change_role(user_id, role, db, current):
    item = locked_user(db, user_id)
    if item.id == current.id and item.role != role:
        raise HTTPException(409, 'Không thể tự thay đổi quyền của tài khoản đang đăng nhập')
    if item.role != role:
        item.role = role
        item.token_version += 1
    db.commit()
    return {'ok': True}


def reset_password(user_id, password, db, current):
    if user_id == current.id:
        raise HTTPException(409, 'Dùng trang Tài khoản để đổi mật khẩu của bạn')
    item = locked_user(db, user_id)
    if verify_password(password, item.password_hash):
        raise HTTPException(400, 'Mật khẩu mới phải khác mật khẩu hiện tại')
    item.password_hash = hash_password(password)
    item.must_change_password = True
    item.token_version += 1
    db.commit()
    return {'ok': True}


def change_password(current, data, db, expected_version):
    item = locked_user(db, current.id)
    if item.token_version != expected_version or not item.is_active:
        raise HTTPException(401, 'Phiên đã bị thu hồi')
    if len(data.current_password.encode('utf-8')) > 72 or not verify_password(data.current_password, item.password_hash):
        raise HTTPException(400, 'Mật khẩu hiện tại không đúng')
    if verify_password(data.password, item.password_hash):
        raise HTTPException(400, 'Mật khẩu mới phải khác mật khẩu hiện tại')
    item.password_hash = hash_password(data.password)
    item.must_change_password = False
    item.token_version += 1
    db.commit()
    db.refresh(item)
    return item
