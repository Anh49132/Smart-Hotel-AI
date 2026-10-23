from datetime import date
from decimal import Decimal
from sqlalchemy import select
from backend.models import User
from backend.api.maintenance import BlockIn
from backend.services.maintenance_service import create_block
from backend.services.booking_service import create_booking
from backend.services.ai_service import available_rooms
from tests.backend.test_booking_consistency import data,concurrent


def test_maintenance_blocks_all_inventory_paths_and_expires(client,db):
    response=client.post('/api/maintenance',json={'room_id':1,'start_date':'2030-01-10','end_date':'2030-01-12','description':'Sửa máy lạnh','assigned_to':1})
    assert response.status_code==200
    assert client.get('/api/rooms?check_in=2030-01-10&check_out=2030-01-12').json()==[]
    assert available_rooms(db,date(2030,1,10),date(2030,1,12),2,Decimal('2000000'))==[]
    cells=client.get('/api/calendar?start=2030-01-10&end=2030-01-13').json()['rooms'][0]['cells']
    assert cells[0]['maintenance'] and not cells[0]['can_book']
    assert not cells[-1]['maintenance'] and cells[-1]['can_book']
    assert client.post('/api/bookings',json=data().model_dump(mode='json')).status_code==409
    assert client.get('/maintenance').status_code==200
    assert client.patch(f"/api/maintenance/{response.json()['id']}",json={'status':'resolved'}).status_code==200
    assert client.get('/api/rooms?check_in=2030-01-10&check_out=2030-01-12').json()


def test_block_cannot_override_booking(client,db):
    create_booking(db,data())
    assert client.post('/api/maintenance',json={'room_id':1,'start_date':'2030-01-11','end_date':'2030-01-13','description':'Sửa cửa'}).status_code==409


def test_concurrent_block_and_booking_are_serialized(db):
    def action(session,index):
        if index: return create_booking(session,data())
        return create_block(session,BlockIn(room_id=1,start_date='2030-01-10',end_date='2030-01-12',description='Sửa cửa'),session.scalar(select(User)))
    assert sorted(concurrent(action))==[200,409]
