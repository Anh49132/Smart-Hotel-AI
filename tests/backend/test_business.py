from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, patch
from fastapi import HTTPException
from backend.models import BookingStatus, ServiceUsage
from backend.schemas import BookingIn
from backend.services.invoice_service import calculate_invoice
from backend.services.booking_service import create_booking, room_is_available


def booking_data(check_in=date(2026,10,15), check_out=date(2026,10,17)):
    return BookingIn(customer_id=1,room_id=1,check_in=check_in,check_out=check_out,guests=2)


def test_create_and_prevent_overlap(db):
    booking = create_booking(db, booking_data())
    assert booking.code.startswith("BK-")
    assert not room_is_available(db, 1, date(2026,10,16), date(2026,10,18))
    try: create_booking(db, booking_data(date(2026,10,16), date(2026,10,18)))
    except HTTPException as exc: assert exc.status_code == 409
    else: assert False, "Phải chặn lịch trùng"


def test_checkout_invoice(db):
    booking = create_booking(db, booking_data())
    booking.status = BookingStatus.checked_out
    db.add(ServiceUsage(booking_id=booking.id, service_id=1, quantity=2, unit_price=50000)); db.commit()
    invoice = calculate_invoice(db, booking)
    assert invoice.room_amount == Decimal("1800000")
    assert invoice.service_amount == Decimal("100000")
    assert invoice.total == Decimal("1900000")


def test_ai_email_mock(client):
    response = client.post("/api/bookings", json={"customer_id":1,"room_id":1,"check_in":"2026-11-01","check_out":"2026-11-03","guests":2})
    booking_id = response.json()["id"]
    with patch("backend.services.ai_service.ollama", new=AsyncMock(return_value="Kính gửi Nguyễn An, đặt phòng đã được xác nhận.")):
        response = client.post("/api/ai/email", json={"booking_id":booking_id,"kind":"confirmation"})
    assert response.status_code == 200
    assert "xác nhận" in response.json()["content"]


def test_ai_chat_mock(client):
    with patch("backend.services.ai_service.ollama_chat", new=AsyncMock(return_value="Hiện có phòng 302 đang trống.")):
        response = client.post("/api/ai/chat", json={"messages":[{"role":"user","content":"Phòng nào đang trống?"}]})
    assert response.status_code == 200
    assert "302" in response.json()["content"]


def test_ai_chat_rejects_invalid_history(client):
    response = client.post("/api/ai/chat", json={"messages":[{"role":"assistant","content":"Tin nhắn cuối không hợp lệ"}]})
    assert response.status_code == 422





def test_complete_stay_and_payment_flow(client, db):
    created = client.post("/api/bookings", json={"customer_id":1,"room_id":1,"check_in":"2027-01-10","check_out":"2027-01-12","guests":2})
    assert created.status_code == 200
    booking_id = created.json()["id"]
    assert client.post(f"/api/bookings/{booking_id}/check-in").status_code == 200
    usage = client.post("/api/service-usages", json={"booking_id":booking_id,"service_id":1,"quantity":2})
    assert usage.status_code == 200
    assert client.post(f"/api/bookings/{booking_id}/check-out").status_code == 200
    from backend.models import Invoice
    invoice = db.query(Invoice).filter_by(booking_id=booking_id).one()
    payment = client.post(f"/api/invoices/{invoice.id}/payments", json={"amount":float(invoice.total)})
    assert payment.status_code == 200
    assert payment.json()["payment_status"] == "paid"


def test_room_availability_endpoint(client):
    response = client.get("/api/rooms?check_in=2028-02-01&check_out=2028-02-03&guests=2")
    assert response.status_code == 200
    assert response.json()[0]["room_type"]["name"] == "Deluxe"
