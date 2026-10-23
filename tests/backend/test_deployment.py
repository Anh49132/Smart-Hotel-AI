import pytest
from fastapi.testclient import TestClient
from backend.main import app

def test_health_and_body_limit(client):
    assert client.get('/healthz').json()=={'status':'ok'}
    response=client.post('/api/bookings',content=b'x'*65537,headers={'content-type':'application/json'})
    assert response.status_code==413

def test_health_failure_hides_details(client,monkeypatch):
    def failed(*args,**kwargs):raise RuntimeError('private-database-password')
    monkeypatch.setattr('backend.main.engine.connect',failed)
    response=client.get('/healthz')
    assert response.status_code==503
    assert response.json()=={'status':'unavailable'}

def test_production_startup_refuses_sqlite(monkeypatch):
    from scripts import start_server
    monkeypatch.setattr(start_server.settings,'app_env','production')
    class Dialect:name='sqlite'
    class Engine:dialect=Dialect()
    monkeypatch.setattr(start_server,'engine',Engine())
    with pytest.raises(RuntimeError,match='PostgreSQL'):start_server.migrate()
