from core.config import settings
from datetime import datetime, timedelta, timezone
from jose import jwt
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)

def create_token(user_id: int, role: str, token_version: int = 0) -> str:
    expires = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    return jwt.encode({"sub": str(user_id), "role": role, "ver": token_version, "exp": expires}, settings.secret_key, algorithm=ALGORITHM)


def set_session_cookie(response, user):
    response.set_cookie("access_token", create_token(user.id, user.role.value, user.token_version),
                        httponly=True, secure=settings.app_env == "production", samesite="lax",
                        max_age=settings.access_token_expire_minutes * 60)
