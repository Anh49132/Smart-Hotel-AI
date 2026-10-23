from sqlalchemy import select
from datetime import datetime
from backend.models import Customer,Booking,BookingStatus,Role,User
from backend.services.booking_service import create_booking
from tests.backend.test_booking_consistency import data
from core.security import hash_password,create_token


def test_history_counts_stays_not_reservations_and_search_pagination(client,db):
    for day,status in [(10,'checked_out'),(12,'checked_in'),(14,'confirmed'),(16,'cancelled'),(18,'no_show')]:
        booking=create_booking(db,data(day));booking.status=BookingStatus(status);db.commit()
        if status=='checked_out':booking.actual_check_out=datetime(2030,1,10,20);db.commit()
    summary=client.get('/api/customers?q=Nguyễn').json()
    assert summary['items'][0]['completed_stays']==1
    assert summary['items'][0]['last_stay']=='2030-01-11'
    detail=client.get('/api/customers/1').json()
    assert detail['counts']=={'checked_out':1,'checked_in':1,'confirmed':1,'cancelled':1,'no_show':1}
    assert client.get('/customers/1').status_code==200
    db.add_all([Customer(full_name=f'Guest {i:02}',phone='0900000000') for i in range(25)]);db.commit()
    assert len(client.get('/api/customers?q=Guest&page=1').json()['items'])==20
    assert len(client.get('/api/customers?q=Guest&page=2').json()['items'])==5
    assert client.get('/customers?q=Guest&page=2').status_code==200
    assert client.get('/api/customers?q=%25').json()['total']==0


def test_identity_masked_and_notes_private_across_api_and_html(client,db):
    guest=db.get(Customer,1);guest.identity_number='123456789012';guest.preference_notes='PRIVATE_PREFERENCE';db.commit()
    booking=create_booking(db,data())
    assert guest.identity_number not in client.get('/api/customers').text
    assert guest.identity_number not in client.get('/customers').text
    assert guest.identity_number not in client.get('/customers/1').text
    reveal=client.get('/api/customers/1/identity')
    assert reveal.json()['identity_number']==guest.identity_number and reveal.headers['cache-control']=='no-store'
    user=User(username='financeguest',full_name='Finance',role=Role.accountant,password_hash=hash_password('Staff@123'))
    db.add(user);db.commit()
    client.cookies.set('access_token',create_token(user.id,'accountant',user.token_version))
    for url in ('/api/customers','/api/customers/1','/customers','/customers/1','/api/bookings',f'/api/bookings/{booking.id}'):
        response=client.get(url)
        assert response.status_code==200
        assert guest.identity_number not in response.text and 'PRIVATE_PREFERENCE' not in response.text
    assert client.get('/api/customers/1/identity').status_code==403


def test_blank_identity_update_preserves_old_and_explicit_clear_works(client,db):
    guest=db.get(Customer,1);guest.identity_number='123456789012';db.commit()
    body={'full_name':guest.full_name,'phone':guest.phone,'email':None,'identity_number':None,'preference_notes':'Phòng yên tĩnh'}
    assert client.put('/api/customers/1',json=body).status_code==200
    db.refresh(guest);assert guest.identity_number=='123456789012'
    omitted={'full_name':guest.full_name,'phone':guest.phone}
    assert client.put('/api/customers/1',json=omitted).status_code==200
    db.refresh(guest);assert guest.preference_notes=='Phòng yên tĩnh'
    body['clear_identity']=True
    assert client.put('/api/customers/1',json=body).status_code==200
    db.refresh(guest);assert guest.identity_number is None
