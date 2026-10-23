from backend.models import Role, User
from core.security import create_token, hash_password
from core.config import Settings, settings
from core.login_limiter import LoginLimiter
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import select
import pytest


def staff(db, role=Role.receptionist):
    user = User(username='staff', full_name='Staff', role=role, password_hash=hash_password('Staff@123'))
    db.add(user)
    db.commit()
    return user


def token(user):
    return create_token(user.id, user.role.value, user.token_version)


def test_change_password_revokes_old_session(client, db):
    old = client.cookies.get('access_token')
    assert client.post('/api/account/password', json={'current_password':'wrong', 'password':'Private@456'}).status_code == 400
    response = client.post('/api/account/password', json={'current_password':'Admin@123', 'password':'Private@456'})
    assert response.status_code == 200
    assert client.get('/api/users').status_code == 200
    client.cookies.set('access_token', old)
    assert client.get('/api/users').status_code == 401
    assert client.post('/login', data={'username':'admin','password':'Admin@123'}).status_code == 401
    assert client.post('/login', data={'username':'admin','password':'Private@456'}).status_code == 200


def test_lock_unlock_and_role_revoke_sessions(client, db):
    user = staff(db)
    old = token(user)
    admin = client.cookies.get('access_token')
    assert client.patch(f'/api/users/{user.id}/active?active=false').status_code == 200
    assert client.post('/login', data={'username':'staff','password':'Staff@123'}).status_code == 401
    assert client.patch(f'/api/users/{user.id}/active?active=true').status_code == 200
    client.cookies.set('access_token', old)
    assert client.get('/api/rooms').status_code == 401
    client.cookies.set('access_token', admin)
    db.refresh(user)
    old = token(user)
    assert client.patch(f'/api/users/{user.id}/role',json={'role':'accountant'}).status_code == 200
    client.cookies.set('access_token', old)
    assert client.get('/api/rooms').status_code == 401


def test_admin_reset_requires_private_password_before_work(client, db):
    user = staff(db)
    assert client.post(f'/api/users/{user.id}/password',json={'password':'Temporary@456'}).status_code == 200
    response = client.post('/login',data={'username':'staff','password':'Temporary@456'},follow_redirects=False)
    assert response.headers['location'] == '/account'
    assert client.get('/account').status_code == 200
    assert client.get('/api/rooms').status_code == 403
    assert client.post('/api/account/password',json={'current_password':'Temporary@456','password':'MyPrivate@789'}).status_code == 200
    assert client.get('/api/rooms').status_code == 200


def test_create_account_validation_and_self_protection(client, db):
    response = client.post('/api/users',json={'username':'newstaff','full_name':'New Staff','password':'Temporary@123','role':'receptionist'})
    assert response.status_code == 200
    user = db.scalar(select(User).where(User.username=='newstaff'))
    assert user.must_change_password
    admin = db.scalar(select(User).where(User.username=='admin'))
    assert client.patch(f'/api/users/{admin.id}/active?active=false').status_code == 409
    assert client.patch(f'/api/users/{admin.id}/role',json={'role':'receptionist'}).status_code == 409
    assert client.post('/api/users',json={'username':'other','full_name':'Other','password':'á'*40,'role':'receptionist'}).status_code == 422
    assert 'password_hash' not in client.get('/api/users').text


@pytest.mark.parametrize('role,users_code,booking_code,payment_code',[
    (Role.admin,200,404,404), (Role.receptionist,403,404,403), (Role.accountant,403,403,404),
])
def test_role_matrix(client, db, role, users_code, booking_code, payment_code):
    user = staff(db,role)
    client.cookies.set('access_token',token(user))
    assert client.get('/api/users').status_code == users_code
    assert client.post('/api/bookings/99999/check-in').status_code == booking_code
    assert client.post('/api/invoices/99999/payments',json={'amount':100}).status_code == payment_code
    for page in ('/rooms','/customers','/bookings','/services','/invoices','/account'):
        result = client.get(page)
        assert result.status_code == 200
        if role == Role.accountant:
            assert 'edit-customer" data-id' not in result.text
            assert 'dropdown-item edit-room' not in result.text


def test_cookie_origin_and_production_settings(client, monkeypatch):
    monkeypatch.setattr(settings,'app_env','production')
    response = client.post('/login',data={'username':'admin','password':'Admin@123'},follow_redirects=False)
    cookie = response.headers['set-cookie']
    assert 'Secure' in cookie and 'HttpOnly' in cookie and 'SameSite=lax' in cookie
    monkeypatch.setattr(settings,'app_env','development')
    assert client.post('/api/users',headers={'Origin':'https://evil.example'},json={}).status_code == 403
    with pytest.raises(ValidationError):
        Settings(_env_file=None,app_env='production',secret_key='short')
    safe = Settings(_env_file=None,app_env='production',secret_key='a'*40)
    assert not safe.auto_create_schema and not safe.seed_demo_data
    with pytest.raises(ValidationError):
        Settings(_env_file=None,bootstrap_admin_password='Admin@123')


def test_login_rate_limit_expires():
    now = [0]
    limiter = LoginLimiter(clock=lambda:now[0])
    for _ in range(5):
        limiter.check('127.0.0.1','admin')
    with pytest.raises(HTTPException) as exc:
        limiter.check('127.0.0.1','admin')
    assert exc.value.status_code == 429
    now[0] = 301
    limiter.check('127.0.0.1','admin')
