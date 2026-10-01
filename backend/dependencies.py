from backend.models import Role, User
from core.config import settings
from core.database import get_db
from core.security import ALGORITHM
from fastapi import Depends, HTTPException, Request, status
from jose import JWTError, jwt
from sqlalchemy.orm import Session

def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    token = request.cookies.get("access_token")
    auth = request.headers.get("Authorization", "")
    if not token and auth.startswith("Bearer "):
        token = auth[7:]
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Vui lòng đăng nhập")
    try:
        user_id = int(jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])["sub"])
    except (JWTError, KeyError, ValueError):
        raise HTTPException(status_code=401, detail="Phiên đăng nhập không hợp lệ")
    user = db.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Tài khoản không hoạt động")
    return user

def require_roles(*roles: Role):
    def dependency(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=403, detail="Bạn không có quyền thực hiện thao tác này")
        return user
    return dependency
