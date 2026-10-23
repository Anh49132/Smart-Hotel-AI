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
        claims = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        user_id = int(claims["sub"])
    except (JWTError, KeyError, ValueError, TypeError):
        raise HTTPException(status_code=401, detail="Phiên đăng nhập không hợp lệ")
    user = db.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Tài khoản không hoạt động")
    if claims.get("ver", 0) != user.token_version:
        raise HTTPException(401, "Phiên đã bị thu hồi. Vui lòng đăng nhập lại")
    if user.must_change_password and request.url.path not in ("/account", "/api/account/password", "/logout"):
        raise HTTPException(403, "Vui lòng vào Tài khoản để đổi mật khẩu tạm thời")
    if user.role == Role.housekeeping and request.url.path not in ('/housekeeping','/account','/api/account/password','/logout') and not request.url.path.startswith('/api/housekeeping'):
        raise HTTPException(403, 'Buồng phòng chỉ truy cập công việc được phân công và tài khoản cá nhân')
    return user

def require_roles(*roles: Role):
    def dependency(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=403, detail="Bạn không có quyền thực hiện thao tác này")
        return user
    return dependency
