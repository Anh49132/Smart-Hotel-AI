import pytest


@pytest.mark.parametrize('path', ['/static/css/style.css', '/static/css/extras.css'])
def test_stylesheets_are_served(client, path):
    response = client.get(path)
    assert response.status_code == 200
    assert 'text/css' in response.headers['content-type']


def test_logged_out_browser_and_api(client):
    client.get('/logout')
    page = client.get('/rooms', follow_redirects=False)
    assert page.status_code == 303
    assert page.headers['location'] == '/login?next=/rooms'
    api = client.get('/api/rooms')
    assert api.status_code == 401
    assert 'detail' in api.json()


def test_non_admin_cannot_manage_users(client, db):
    from backend.models import Role, User
    from core.security import create_token

    user = db.get(User, 1)
    user.role = Role.receptionist
    db.commit()
    client.cookies.set('access_token', create_token(user.id, user.role.value))
    assert client.get('/users').status_code == 403
    assert client.get('/api/users').status_code == 403
