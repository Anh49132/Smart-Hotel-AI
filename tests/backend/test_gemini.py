import asyncio
import json

import httpx
import pytest
from pydantic import SecretStr

from backend.services import gemini_client
from backend.services.ai_service import generate_chat
from core.config import settings


TEST_KEY = "unit-test-gemini-key"
TEXT = "Kính gửi Quý khách, thông tin đặt phòng đã được xác nhận."


def answer(parts=None, finish="STOP"):
    return {"candidates": [{"finishReason": finish, "content": {"role": "model", "parts": parts or [{"text": TEXT}]}}]}


@pytest.fixture
def transport(monkeypatch):
    monkeypatch.setattr(settings, "gemini_api_key", SecretStr(TEST_KEY))
    monkeypatch.setattr(settings, "gemini_model", "gemini-3.5-flash-lite")
    original_client = httpx.AsyncClient
    state = {"requests": [], "response": answer(), "status": 200}

    def handle(request):
        state["requests"].append(request)
        if state.get("exception"):
            raise state["exception"]("test transport failure", request=request)
        if "raw" in state:
            return httpx.Response(state["status"], content=state["raw"])
        return httpx.Response(state["status"], json=state["response"])

    monkeypatch.setattr(
        gemini_client.httpx, "AsyncClient",
        lambda *args, **kwargs: original_client(*args, transport=httpx.MockTransport(handle), **kwargs),
    )
    return state


def test_credentials_only_in_header_and_answer_parts(transport):
    transport["response"] = answer([
        {"text": "internal reasoning", "thought": True},
        {"text": "Xin chào"},
        {"text": "Đặt phòng đã được xác nhận."},
    ])
    output = asyncio.run(gemini_client.generate_text(f"Yêu cầu chứa key {TEST_KEY}", "Trợ lý khách sạn"))
    request = transport["requests"][0]
    assert request.url.host == "generativelanguage.googleapis.com"
    assert request.url.path.endswith("/models/gemini-3.5-flash-lite:generateContent")
    assert not request.url.query
    assert request.headers["x-goog-api-key"] == TEST_KEY
    assert TEST_KEY not in request.content.decode()
    payload = json.loads(request.content)
    assert payload["systemInstruction"]["parts"][0]["text"] == "Trợ lý khách sạn"
    assert payload["contents"][0]["role"] == "user"
    assert output == "Xin chào\nĐặt phòng đã được xác nhận."


def test_chat_history_and_sensitive_data_filtered_before_transport(transport):
    messages = [
        {"role": "assistant", "content": "Previous turn outside retained conversation"},
        {"role": "user", "content": "Cần phòng cho 2 khách"},
        {"role": "assistant", "content": "Ngân sách của bạn là bao nhiêu?"},
        {"role": "user", "content": f"CCCD: 012345678901; số thẻ: 4111 1111 1111 1111; password: VeryPrivate123; key {TEST_KEY}. Ngân sách 900000."},
    ]
    output = asyncio.run(generate_chat(messages, {"tong_so_phong": 4, "tong_tien_con_phai_thu": 123456789}))
    payload = json.loads(transport["requests"][0].content)
    serialized = json.dumps(payload, ensure_ascii=False)
    assert [turn["role"] for turn in payload["contents"]] == ["user", "model", "user"]
    for sensitive in ("012345678901", "4111 1111 1111 1111", "VeryPrivate123", TEST_KEY):
        assert sensitive not in serialized
    assert "900000" in serialized
    assert "123456789" in payload["systemInstruction"]["parts"][0]["text"]
    assert "NGỮ CẢNH" in serialized
    assert output == TEXT


@pytest.mark.parametrize("kind", ["confirmation", "cancellation", "payment_reminder"])
def test_email_uses_gemini_without_sensitive_customer_fields(client, db, transport, kind):
    from backend.models import Customer

    customer = db.get(Customer, 1)
    customer.identity_number = "012345678901"
    customer.email = "private@example.com"
    db.commit()
    booking = client.post("/api/bookings", json={"customer_id": 1, "room_id": 1, "check_in": "2030-11-01", "check_out": "2030-11-03", "guests": 2, "note": "PRIVATE_BOOKING_NOTE"}).json()
    response = client.post("/api/ai/email", json={"booking_id": booking["id"], "kind": kind})
    assert response.status_code == 200
    assert response.json()["content"] == TEXT
    assert response.json()["review_status"] == "pending"
    sent = transport["requests"][0].content.decode()
    for sensitive in (customer.identity_number, customer.phone, customer.email, "PRIVATE_BOOKING_NOTE"):
        assert sensitive not in sent
    assert kind in sent


def test_room_advice_and_report_use_gemini(client, transport):
    response = client.post("/api/ai/room-advice", json={"guests": 2, "budget": 1000000, "check_in": "2030-11-01", "check_out": "2030-11-03", "amenities": "Bồn tắm"})
    assert response.status_code == 200
    assert response.json()["message"] == TEXT
    assert response.json()["rooms"][0]["number"] == "302"
    assert client.get("/api/ai/report").json()["content"] == TEXT
    assert len(transport["requests"]) == 2


def test_no_matching_room_does_not_consume_quota(client, transport):
    response = client.post("/api/ai/room-advice", json={"guests": 2, "budget": 1, "check_in": "2030-11-01", "check_out": "2030-11-03"})
    assert response.status_code == 200
    assert response.json()["rooms"] == []
    assert transport["requests"] == []


def test_missing_key_does_not_call_provider(client, transport, monkeypatch):
    monkeypatch.setattr(settings, "gemini_api_key", SecretStr(""))
    response = client.post("/api/ai/chat", json={"messages": [{"role": "user", "content": "Xin chào"}]})
    assert response.status_code == 503
    assert "GEMINI_API_KEY" in response.json()["detail"]
    assert transport["requests"] == []


@pytest.mark.parametrize("status, expected", [(400, "cấu hình"), (401, "API key"), (403, "API key"), (404, "GEMINI_MODEL"), (429, "hạn mức"), (500, "thử lại")])
def test_provider_errors_are_actionable_and_hide_raw_details(client, transport, status, expected):
    transport.update(status=status, response={"error": {"message": f"raw provider secret {TEST_KEY}"}})
    response = client.post("/api/ai/chat", json={"messages": [{"role": "user", "content": "Xin chào"}]})
    assert response.status_code == 503
    assert expected in response.json()["detail"]
    assert TEST_KEY not in response.text
    assert "raw provider" not in response.text
    assert len(transport["requests"]) == 1


@pytest.mark.parametrize("exception, expected", [(httpx.ReadTimeout, "quá lâu"), (httpx.ConnectError, "Internet")])
def test_timeout_and_connection_errors(client, transport, exception, expected):
    transport["exception"] = exception
    response = client.post("/api/ai/chat", json={"messages": [{"role": "user", "content": "Xin chào"}]})
    assert response.status_code == 503
    assert expected in response.json()["detail"]


@pytest.mark.parametrize("body", [{}, [], {"candidates": []}, {"candidates": None}, {"candidates": [{"content": None}]}, answer([{"text": "   "}]), answer([{"text": "hidden", "thought": True}])])
def test_invalid_response_never_returns_success(client, transport, body):
    transport["response"] = body
    response = client.post("/api/ai/chat", json={"messages": [{"role": "user", "content": "Xin chào"}]})
    assert response.status_code == 502
    assert "không hợp lệ" in response.json()["detail"]


def test_invalid_json_response(client, transport):
    transport["raw"] = b"not json"
    response = client.post("/api/ai/chat", json={"messages": [{"role": "user", "content": "Xin chào"}]})
    assert response.status_code == 502


@pytest.mark.parametrize("body, status", [({"promptFeedback": {"blockReason": "SAFETY"}}, 422), (answer(finish="SAFETY"), 422), (answer(finish="MAX_TOKENS"), 502)])
def test_blocked_and_incomplete_responses_not_saved_as_drafts(client, db, transport, body, status):
    from backend.models import AIResult

    booking = client.post("/api/bookings", json={"customer_id": 1, "room_id": 1, "check_in": "2030-11-01", "check_out": "2030-11-03", "guests": 2}).json()
    transport["response"] = body
    response = client.post("/api/ai/email", json={"booking_id": booking["id"], "kind": "confirmation"})
    assert response.status_code == status
    assert db.query(AIResult).count() == 0
