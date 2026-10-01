from backend.models import User
from core.security import verify_password
from sqlalchemy import select
from sqlalchemy.orm import Session
from typing import Optional

def authenticate(db: Session, username: str, password: str) -> Optional[User]:
    user = db.scalar(select(User).where(User.username == username))
    return user if user and verify_password(password, user.password_hash) else None
