from .inventory_service import blocked_rooms
from .booking_service import ACTIVE_BOOKING_STATUSES
from .rates_service import quote
from backend.models import Booking, BookingStatus, HotelService, Invoice, Room, RoomStatus, RoomType
from .gemini_client import generate_content, generate_text, sanitize_free_text
from datetime import date
from decimal import Decimal
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

import json


ROOM_SYSTEM = """Bạn là trợ lý lễ tân khách sạn. Chỉ đề xuất phòng trong danh sách được cung cấp, tối đa 3 phòng. Không bịa dữ liệu. Trả lời tiếng Việt ngắn gọn."""
EMAIL_SYSTEM = """Bạn soạn email nghiệp vụ khách sạn lịch sự bằng tiếng Việt. Chỉ dùng dữ liệu được cung cấp. Không thêm số giấy tờ, dữ liệu thanh toán hay thông tin không có."""
REPORT_SYSTEM = """Bạn là trợ lý phân tích khách sạn. Viết báo cáo ngắn từ đúng số liệu đã cung cấp và đề xuất tối đa 3 khuyến mãi khả thi. Không bịa số liệu."""
CHAT_SYSTEM = """Bạn là chatbot nội bộ của Lotus Hotel AI, trả lời bằng tiếng Việt rõ ràng và thân thiện.
Chỉ sử dụng dữ liệu khách sạn được cung cấp trong phần NGỮ CẢNH. Không bịa số liệu, phòng, giá hoặc trạng thái.
Bạn có thể giải thích quy trình đặt phòng, nhận phòng, trả phòng, dịch vụ, hóa đơn và cách dùng hệ thống.
Không được nói rằng bạn đã tạo, sửa, hủy hay thanh toán bất kỳ bản ghi nào; chatbot chỉ tư vấn.
Không yêu cầu hoặc tiết lộ số giấy tờ, mật khẩu, token hay chi tiết thanh toán cá nhân.
Nếu câu hỏi nằm ngoài dữ liệu hoặc nghiệp vụ khách sạn, hãy nói ngắn gọn rằng bạn chưa có đủ thông tin.
Khi đề xuất phòng, chỉ chọn phòng có trạng thái Trống và nhắc nhân viên kiểm tra ngày lưu trú trên màn hình Đặt phòng."""


async def generate_chat(messages: list[dict], context: dict) -> str:
    system = f"{CHAT_SYSTEM}\n\nNGỮ CẢNH DỮ LIỆU HIỆN TẠI:\n{json.dumps(context, ensure_ascii=False)}"
    contents = []
    for message in messages:
        role = "model" if message["role"] == "assistant" else "user"
        # A retained history can start with an assistant turn after trimming.
        if not contents and role == "model":
            continue
        part = {"text": sanitize_free_text(message["content"])}
        if contents and contents[-1]["role"] == role:
            contents[-1]["parts"].append(part)
        else:
            contents.append({"role": role, "parts": [part]})
    return await generate_content(contents, system)


def chatbot_context(db: Session) -> dict:
    rooms = db.scalars(
        select(Room).join(RoomType).where(RoomType.is_active.is_(True)).options(selectinload(Room.room_type)).order_by(Room.number)
    ).all()
    services = db.scalars(
        select(HotelService).where(HotelService.active == True).order_by(HotelService.name)
    ).all()
    status_labels = {
        RoomStatus.available: "Trống",
        RoomStatus.occupied: "Đang ở",
        RoomStatus.cleaning: "Đang dọn",
        RoomStatus.maintenance: "Bảo trì",
    }
    room_counts = {
        label: sum(room.status == status for room in rooms)
        for status, label in status_labels.items()
    }
    active_bookings = db.scalar(
        select(func.count(Booking.id)).where(Booking.status.in_(ACTIVE_BOOKING_STATUSES))
    ) or 0
    arrivals_today = db.scalar(
        select(func.count(Booking.id)).where(
            Booking.check_in == date.today(), Booking.status == BookingStatus.confirmed
        )
    ) or 0
    outstanding = db.scalar(
        select(func.coalesce(func.sum(Invoice.total - Invoice.paid_amount), 0)).where(
            Invoice.paid_amount < Invoice.total
        )
    ) or 0
    return {
        "ngay_hien_tai": str(date.today()),
        "tong_so_phong": len(rooms),
        "so_luong_theo_trang_thai": room_counts,
        "phong": [
            {
                "so_phong": sanitize_free_text(room.number),
                "loai": sanitize_free_text(room.room_type.name),
                "suc_chua": room.room_type.capacity,
                "gia_moi_dem": float(room.room_type.nightly_rate),
                "tien_ich": sanitize_free_text(room.room_type.amenities),
                "trang_thai": status_labels.get(room.status, room.status.value),
            }
            for room in rooms
        ],
        "dich_vu_dang_hoat_dong": [
            {"ten": sanitize_free_text(service.name), "don_vi": sanitize_free_text(service.unit), "gia": float(service.price)}
            for service in services
        ],
        "so_dat_phong_dang_hieu_luc": active_bookings,
        "so_khach_du_kien_den_hom_nay": arrivals_today,
        "tong_tien_con_phai_thu": float(outstanding),
    }


async def hotel_chat(db: Session, messages) -> str:
    safe_messages = [
        {"role": message.role, "content": message.content}
        for message in messages[-12:]
    ]
    return await generate_chat(safe_messages, chatbot_context(db))


def available_rooms(db: Session, check_in, check_out, guests: int, budget: Decimal):
    blocked = blocked_rooms(check_in, check_out)
    rooms = db.scalars(select(Room).join(RoomType).where(Room.id.not_in(blocked), RoomType.capacity >= guests, RoomType.is_active.is_(True), Room.status != RoomStatus.maintenance)).all()
    # A nightly budget is a ceiling for every night, including weekend/holiday prices.
    prices = {}
    result = []
    for room in rooms:
        if room.room_type_id not in prices:
            prices[room.room_type_id] = quote(db, room.room_type, check_in, check_out)
        if all(n['amount'] <= budget for n in prices[room.room_type_id]['nights']):
            result.append(room)
    return result


async def advise_rooms(db: Session, data) -> dict:
    rooms = available_rooms(db, data.check_in, data.check_out, data.guests, data.budget)
    if not rooms:
        return {"message": "Không có phòng phù hợp và còn trống trong khoảng ngày đã chọn.", "rooms": []}
    safe = []
    for r in rooms:
        prices = quote(db, r.room_type, data.check_in, data.check_out)
        safe.append({"number": sanitize_free_text(r.number), "type": sanitize_free_text(r.room_type.name), "capacity": r.room_type.capacity,
                     "price": float(prices['average']), "stay_total": float(prices['total']), "price_basis": "Trung bình mỗi đêm; tổng theo ngày lưu trú",
                     "amenities": sanitize_free_text(r.room_type.amenities)})
    prompt = f"Nhu cầu: {data.guests} khách, ngân sách {data.budget}/đêm, từ {data.check_in} đến {data.check_out}, tiện ích: {sanitize_free_text(data.amenities) or 'không yêu cầu'}. Danh sách phòng trống: {json.dumps(safe, ensure_ascii=False)}"
    return {"message": await generate_text(prompt, ROOM_SYSTEM), "rooms": safe[:3]}


async def booking_email(db: Session, booking_id: int, kind: str) -> str:
    booking = db.get(Booking, booking_id)
    if not booking:
        raise HTTPException(404, "Không tìm thấy đặt phòng")
    safe = {"customer_name": sanitize_free_text(booking.customer.full_name), "booking_code": booking.code, "room": sanitize_free_text(booking.room.number), "room_type": sanitize_free_text(booking.room.room_type.name), "check_in": str(booking.check_in), "check_out": str(booking.check_out), "status": booking.status.value}
    return await generate_text(f"Loại email: {kind}. Dữ liệu đặt phòng: {json.dumps(safe, ensure_ascii=False)}", EMAIL_SYSTEM)


async def ai_report(db: Session) -> str:
    total_rooms = db.scalar(select(func.count(Room.id))) or 0
    occupied = db.scalar(select(func.count(Room.id)).where(Room.status == RoomStatus.occupied)) or 0
    revenue = db.scalar(select(func.coalesce(func.sum(Invoice.paid_amount), 0))) or 0
    bookings = db.scalar(select(func.count(Booking.id)).where(Booking.status.not_in((BookingStatus.cancelled,BookingStatus.no_show)))) or 0
    data = {"total_rooms": total_rooms, "occupied_rooms": occupied, "occupancy_percent": round(occupied / total_rooms * 100, 1) if total_rooms else 0, "paid_revenue": float(revenue), "active_bookings": bookings}
    return await generate_text(f"Số liệu hiện tại: {json.dumps(data, ensure_ascii=False)}", REPORT_SYSTEM)
