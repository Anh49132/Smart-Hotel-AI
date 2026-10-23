from datetime import date
from backend.models import Room
from backend.services.booking_service import create_booking
from tests.backend.test_booking_consistency import data


def test_calendar_half_open_and_filters(client,db):
    booking=create_booking(db,data())
    db.add(Room(id=2,number='401',floor=4,room_type_id=1)); db.commit()
    result=client.get('/api/calendar?start=2030-01-10&end=2030-01-13&floor=3&type_id=1&guests=2').json()
    assert result['total']==1 and len(result['days'])==3
    cells=result['rooms'][0]['cells']
    assert cells[0]['bookings'][0]['id']==booking.id
    assert cells[1]['can_book'] is False and cells[2]['can_book'] is True
    assert client.get('/calendar?start=2030-01-10&end=2030-01-13').status_code==200
    assert client.get('/api/calendar?start=2030-01-10&end=2030-03-13').status_code==422
    assert client.get('/api/calendar?start=2030-01-10&end=2030-01-13&guests=3').json()['rooms']==[]
    assert client.get('/api/rooms?floor=4&type_id=1').json()[0]['number']=='401'


def test_calendar_empty_and_unauthenticated(client):
    result=client.get('/calendar?floor=99')
    assert result.status_code==200 and 'Không có phòng phù hợp' in result.text
    client.cookies.clear()
    assert client.get('/api/calendar?start=2030-01-10&end=2030-01-11').status_code==401
