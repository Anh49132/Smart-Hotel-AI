from backend.models import User
from core.security import verify_password
from sqlalchemy import select
from sqlalchemy.orm import Session
from typing import Optional

def authenticate(db: Session, username: str, password: str) -> Optional[User]:
    user = db.scalar(select(User).where(User.username == username))
    if len(password.encode('utf-8')) > 72:
        return None
    return user if user and user.is_active and verify_password(password, user.password_hash) else None
