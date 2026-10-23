import json
from unittest.mock import AsyncMock
from sqlalchemy import select,func
from backend.models import AIResult,AIReviewEvent,Booking,BookingStatus,BookingChange,Customer,Role
from backend.services.booking_service import create_booking
from backend.api.ai import review_ai_result
from backend.models import User
from tests.backend.test_booking_consistency import data,concurrent
from tests.backend.test_staff_security import staff,token


def test_email_types_provenance_privacy_and_review(client,db,monkeypatch):
    mocked=AsyncMock(return_value='Kính gửi Quý khách, cảm ơn đã lựa chọn khách sạn.')
    monkeypatch.setattr('backend.services.ai_service.generate_text',mocked)
    b=create_booking(db,data());bid=b.id
    c=db.get(Customer,1);c.identity_number='012345678901';c.preference_notes='PRIVATE_PREFERENCES';c.email='private@example.com';db.commit()
    for kind in ('confirmation','payment_reminder'):
        r=client.post('/api/ai/email',json={'booking_id':bid,'kind':kind});assert r.status_code==200
        detail=client.get(f"/api/ai/results/{r.json()['ai_result_id']}").json()
        assert detail['prompt_version']=='booking-email-v2' and detail['model']!='legacy/unknown'
        assert client.get(f"/ai/results/{r.json()['ai_result_id']}/print").status_code==200
    assert client.post('/api/ai/email',json={'booking_id':bid,'kind':'change'}).status_code==409
    db.add(BookingChange(booking_id=bid,changed_by=1,reason='Changed dates',before_data='{}',after_data='{}'));db.commit()
    assert client.post('/api/ai/email',json={'booking_id':bid,'kind':'change'}).status_code==200
    assert client.post('/api/ai/email',json={'booking_id':bid,'kind':'cancellation'}).status_code==409
    db.get(Booking,bid).status=BookingStatus.cancelled;db.commit()
    r=client.post('/api/ai/email',json={'booking_id':bid,'kind':'cancellation'});assert r.status_code==200
    for call in mocked.call_args_list:
        assert all(secret not in call.args[0] for secret in ('012345678901','private@example.com','PRIVATE_PREFERENCES','0900000000'))
    result_id=r.json()['ai_result_id']
    assert sorted(concurrent(lambda s,i:review_ai_result(result_id,bool(i),s,s.get(User,1))))==[200,409]
    assert db.scalar(select(func.count()).select_from(AIReviewEvent))==1
    clerk=staff(db,Role.receptionist);client.cookies.set('access_token',token(clerk))
    assert client.get(f'/api/ai/results/{result_id}').status_code==403
    assert client.get('/api/ai/results').json()==[]


def test_email_race_does_not_save_stale_draft(client,db,monkeypatch):
    b=create_booking(db,data());bid=b.id
    async def generate(*args):
        db.get(Booking,bid).status=BookingStatus.cancelled;db.commit()
        return 'Đặt phòng đã xác nhận'
    monkeypatch.setattr('backend.services.ai_service.generate_text',generate)
    assert client.post('/api/ai/email',json={'booking_id':bid,'kind':'confirmation'}).status_code==409
    assert db.scalar(select(func.count()).select_from(AIResult))==0


def test_known_booking_code_is_preserved_but_identity_is_redacted(client,db,monkeypatch):
    b=create_booking(db,data());b.code='BK-A1234567';db.commit()
    monkeypatch.setattr('backend.services.ai_service.generate_text',AsyncMock(return_value='Mã BK-A1234567; CCCD: 012345678901'))
    result=client.post('/api/ai/email',json={'booking_id':b.id,'kind':'confirmation'})
    assert result.status_code==200
    assert 'BK-A1234567' in result.json()['content'] and '012345678901' not in result.json()['content']
