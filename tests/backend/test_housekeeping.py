from backend.models import User,Role,Room,CleaningTask,RoomStatus
from core.security import hash_password,create_token
from sqlalchemy import select
from backend.services.booking_service import create_booking,booking_action
from tests.backend.test_booking_consistency import data


def test_checkout_assign_clean_inspect_and_isolated_role(client,db):
    booking=create_booking(db,data()); booking_action(booking.id,'check-in',db); booking_action(booking.id,'check-out',db)
    task=db.scalar(select(CleaningTask))
    user=User(username='cleaner',full_name='Cleaner',role=Role.housekeeping,password_hash=hash_password('Staff@123'))
    db.add(user);db.commit()
    task_id,user_id=task.id,user.id
    assert client.patch('/api/rooms/1/status?status=available').status_code==409
    assert client.post(f'/api/housekeeping/{task_id}',json={'action':'assign','assigned_to':user_id}).status_code==200
    admin=client.cookies.get('access_token')
    client.cookies.set('access_token',create_token(user_id,'housekeeping',user.token_version))
    assert client.get('/housekeeping').status_code==200
    for url in ('/api/customers','/api/bookings','/api/users','/api/rooms','/api/ai/report','/bookings'):
        assert client.get(url).status_code==403
    assert 'customer' not in str(client.get('/api/housekeeping').json())
    assert client.post(f'/api/housekeeping/{task_id}',json={'action':'start'}).status_code==200
    assert client.post(f'/api/housekeeping/{task_id}',json={'action':'complete'}).status_code==200
    assert client.post(f'/api/housekeeping/{task_id}',json={'action':'inspect'}).status_code==403
    client.cookies.set('access_token',admin)
    assert client.post(f'/api/housekeeping/{task_id}',json={'action':'inspect'}).status_code==200
    db.refresh(task);db.refresh(db.get(Room,1))
    assert task.inspected_at and task.completed_at and db.get(Room,1).status==RoomStatus.available
