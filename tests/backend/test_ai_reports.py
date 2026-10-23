import json
from unittest.mock import AsyncMock
import pytest
from sqlalchemy import select,func
from backend.models import AIResult,CashierShift,Role
from core.ai_limiter import AIBudget
from fastapi import HTTPException
from tests.backend.test_staff_security import staff,token


def test_report_is_grounded_and_rejects_invented_values(client,db,monkeypatch):
    mocked=AsyncMock(return_value=json.dumps({'highlights':[{'key':'occupancy','value':'0.0'},{'key':'net_cash','value':'0'}],'promotion_codes':['weekday']}))
    monkeypatch.setattr('backend.services.ai_reports.generate_structured',mocked)
    url='/api/ai/report?start=2030-01-01&end=2030-02-01'
    result=client.post(url,json={});assert result.status_code==200
    assert 'Công suất' in result.json()['content']
    saved=db.get(AIResult,result.json()['ai_result_id'])
    assert saved.prompt_version=='operating-report-v2' and saved.source_json
    mocked.return_value=json.dumps({'highlights':[{'key':'occupancy','value':'99.9'}],'promotion_codes':[]})
    assert client.post(url,json={}).status_code==502
    assert db.scalar(select(func.count()).select_from(AIResult))==1
    clerk=staff(db,Role.receptionist);client.cookies.set('access_token',token(clerk))
    assert client.post(url,json={}).status_code==403


def test_handover_scope_excludes_notes_and_references(client,db,monkeypatch):
    mocked=AsyncMock(return_value=json.dumps({'focus':['cash','pending']}))
    monkeypatch.setattr('backend.services.ai_reports.generate_structured',mocked)
    db.get(CashierShift,1).note='PRIVATE_STAFF_HANDOVER_NOTE';db.commit()
    result=client.post('/api/ai/handover/1',json={})
    assert result.status_code==200 and 'Tiền mặt' in result.json()['content']
    assert 'PRIVATE_STAFF_HANDOVER_NOTE' not in mocked.call_args.args[0]
    clerk=staff(db,Role.receptionist);client.cookies.set('access_token',token(clerk))
    assert client.post('/api/ai/handover/1',json={}).status_code==403
    assert mocked.await_count==1


def test_ai_budget_limits_inflight_and_rate():
    budget=AIBudget()
    with budget.reserve(1),budget.reserve(1):
        with pytest.raises(HTTPException) as error:
            with budget.reserve(1):pass
        assert error.value.status_code==429
    for _ in range(8):
        with budget.reserve(1):pass
    with pytest.raises(HTTPException):
        with budget.reserve(1):pass
    with budget.reserve(2):pass


def test_reception_chat_does_not_send_hotel_finances(client,db,monkeypatch):
    mocked=AsyncMock(return_value='Dữ liệu này cần quyền kế toán.')
    monkeypatch.setattr('backend.services.ai_service.generate_chat',mocked)
    clerk=staff(db,Role.receptionist);client.cookies.set('access_token',token(clerk))
    assert client.post('/api/ai/chat',json={'messages':[{'role':'user','content':'Công nợ cả khách sạn?'}]}).status_code==200
    assert 'tong_tien_con_phai_thu' not in mocked.call_args.args[1]
