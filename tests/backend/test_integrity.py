import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError


def book(client):
    return client.post('/api/bookings', json={'customer_id':1,'room_id':1,'check_in':'2030-01-10','check_out':'2030-01-12','guests':2})


def test_invalid_customer_rejected_and_session_recovers(client):
    data={'customer_id':99999,'room_id':1,'check_in':'2030-01-10','check_out':'2030-01-12','guests':2}
    assert client.post('/api/bookings',json=data).status_code == 404
    assert book(client).status_code == 200


def test_history_cannot_be_deleted(client):
    assert book(client).status_code == 200
    assert client.delete('/api/rooms/1').status_code == 409
    assert client.delete('/api/customers/1').status_code == 409
    assert client.get('/bookings').status_code == 200


def test_invalid_room_type_update_is_rejected(client):
    response=client.put('/api/rooms/1',json={'number':'302','floor':3,'room_type_id':999,'status':'available'})
    assert response.status_code == 404


def test_foreign_key_enforced_for_direct_writes(db):
    with pytest.raises(IntegrityError):
        db.execute(text("INSERT INTO rooms(number,floor,status,room_type_id) VALUES('999',1,'available',999999)"))
        db.commit()
    db.rollback()


def test_invalid_quantity_enforced_for_direct_writes(db):
    with pytest.raises(IntegrityError):
        db.execute(text("UPDATE room_types SET capacity=0 WHERE id=1"))
        db.commit()
    db.rollback()
