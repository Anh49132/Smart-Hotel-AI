from .inventory_service import blocked_rooms
from .booking_service import ACTIVE_BOOKING_STATUSES
from .rates_service import quote
from backend.models import Booking, BookingStatus, Customer, HotelPolicy, HotelService, Invoice, Room, RoomStatus, RoomType,Role,FinancialAdjustment
from .gemini_client import generate_content, generate_text, sanitize_free_text
from datetime import date
from core.hotel_time import hotel_today
from decimal import Decimal
from fastapi import HTTPException
from sqlalchemy import func, select, case
from sqlalchemy.orm import Session, selectinload
import re
import unicodedata

import json


ROOM_SYSTEM = """Bạn là trợ lý lễ tân khách sạn. Chỉ đề xuất phòng trong danh sách được cung cấp, tối đa 3 phòng. Không bịa dữ liệu. Trả lời tiếng Việt ngắn gọn."""
EMAIL_SYSTEM = """Bạn soạn email nghiệp vụ khách sạn lịch sự bằng tiếng Việt. Chỉ dùng dữ liệu được cung cấp. Không thêm số giấy tờ, dữ liệu thanh toán hay thông tin không có."""
REPORT_SYSTEM = """Bạn là trợ lý phân tích khách sạn. Viết báo cáo ngắn từ đúng số liệu đã cung cấp và đề xuất tối đa 3 khuyến mãi khả thi. Không bịa số liệu."""
CHAT_SYSTEM = """Bạn là trợ lý hội thoại của Lotus Hotel, trả lời bằng tiếng Việt tự nhiên, ấm áp và gọn.
Trả lời trực tiếp câu hỏi trước, rồi mới giải thích ngắn nếu cần. Không lặp đi lặp lại một câu từ chối có sẵn.
Với chào hỏi, nói chuyện vui hoặc yêu cầu giải trí, phản hồi thân thiện; nếu yêu cầu âm thanh thì nói rõ bạn chỉ trả lời bằng văn bản và có thể đề nghị một lựa chọn phù hợp.
Với thông tin khách sạn, chỉ khẳng định dữ kiện có trong NGỮ CẢNH. Không tự bịa giá, tiện ích, doanh thu, trạng thái hay quy định.
Nếu dữ liệu chưa ghi nhận một tiện ích, nói rõ là danh mục hiện chưa ghi nhận, không kết luận chắc chắn khách sạn không có; gợi ý nơi nhân viên có thể cập nhật.
Nếu thiếu dữ kiện, nêu chính xác đang thiếu trường nào và cách kiểm tra trong ứng dụng, thay vì trả lời chung chung.
Khi có báo cáo tháng trong ngữ cảnh, dùng đúng kỳ và số đã tổng hợp; phân biệt doanh thu hóa đơn với tiền thực thu/hoàn, không tự tính lại.
Không tiết lộ dữ liệu cá nhân khách hàng, giấy tờ, mật khẩu, token hay thông tin thanh toán; hướng nhân viên tới mục Khách hàng để tra cứu theo quyền.
Không nói rằng bạn đã tạo, sửa, hủy hay thanh toán bản ghi; chatbot chỉ tư vấn.
Khi gợi ý phòng, chỉ dùng phòng trạng thái Trống và nhắc nhân viên kiểm tra ngày lưu trú trên màn hình Đặt phòng."""

def _normalize_chat_text(value:str)->str:
    return ''.join(ch for ch in unicodedata.normalize('NFD',value.lower()) if unicodedata.category(ch)!='Mn')

def _is_customer_lookup(value:str)->bool:
    text=_normalize_chat_text(value)
    refers_to_customer='khach hang' in text or 'ho so khach' in text or ('khach' in text and any(term in text for term in ('thong tin','ho so','lich su','so dien thoai','email')))
    return refers_to_customer and any(term in text for term in ('thong tin','ho so','lich su','lien lac','so dien thoai','email','dat phong'))

def _customer_lookup_reply(db,question:str,user)->str|None:
    if not _is_customer_lookup(question):return None
    if user is None or user.role not in (Role.admin,Role.receptionist):
        return 'Hồ sơ khách cần được tra cứu tại mục Khách hàng theo quyền của tài khoản. Mình không đưa thông tin cá nhân vào cuộc trò chuyện với AI.'
    normalized=_normalize_chat_text(question)
    match=re.search(r'khach hang\s+(.+)',normalized)
    if not match:
        return 'Bạn nhập tên khách cần tìm, rồi mở mục Khách hàng để xem hồ sơ và lịch sử lưu trú.'
    words=re.findall(r'[a-z0-9]+',match.group(1))
    stop={'la','gi','the','nao','giup','toi','nhe','trong','he','thong','khong','co','cho','xem'}
    while words and words[-1] in stop:words.pop()
    names=db.scalars(select(Customer).order_by(Customer.id)).all()
    query=' '.join(words)
    matches=[item for item in names if query and (lambda name: name==query or name.startswith(query+' '))(_normalize_chat_text(item.full_name))]
    if not matches:
        return f'Chưa tìm thấy hồ sơ khớp với “{query or "tên khách"}”. Bạn có thể kiểm tra cách viết hoặc tra cứu trực tiếp trong mục Khách hàng.'
    if len(matches)>1:
        return f'Có nhiều hồ sơ gần khớp với “{query}”. Hãy mở mục Khách hàng và tìm đầy đủ họ tên để chọn đúng người.'
    customer=matches[0]
    bookings=db.scalars(select(Booking).where(Booking.customer_id==customer.id).order_by(Booking.check_in.desc(),Booking.id.desc())).all()
    completed=[item for item in bookings if item.status==BookingStatus.checked_out]
    active=[item for item in bookings if item.status in (BookingStatus.confirmed,BookingStatus.checked_in)]
    last_stay=max((item.actual_check_out.date() if item.actual_check_out else item.check_out for item in completed),default=None)
    summary=f'Đã tìm thấy hồ sơ {customer.full_name}: {len(completed)} lượt lưu trú đã hoàn tất, {len(active)} lịch đang xác nhận hoặc lưu trú.'
    if last_stay:summary+=f' Lần lưu trú hoàn tất gần nhất: {last_stay.isoformat()}.'
    return summary+' Số điện thoại, email và giấy tờ không hiển thị trong chat; mở mục Khách hàng để xem theo quyền.'

def _month_report_context(db, latest_question:str, user, conversation_context:str|None=None)->dict|None:
    if user is None or user.role not in (Role.admin,Role.accountant):return None
    latest=_normalize_chat_text(latest_question)
    text=_normalize_chat_text(conversation_context or latest_question)
    if not any(term in text for term in ('doanh thu','cong suat','dat phong','bao cao','thu tien','tien thu','so lieu')):return None
    today=hotel_today()
    if any(term in latest for term in ('thang truoc','thang vua roi')):
        year,month=(today.year-1,12) if today.month==1 else (today.year,today.month-1)
    elif any(term in latest for term in ('thang nay','thang hien tai')):
        year,month=today.year,today.month
    else:
        month_pattern=r'\bthang\s+(0?[1-9]|1[0-2])\b'
        year_text=latest
        matches=list(re.finditer(month_pattern,latest))
        if not matches:
            year_text=text
            matches=list(re.finditer(month_pattern,text))
        if not matches:return None
        match=matches[-1]
        years=re.findall(r'\b20\d{2}\b',year_text)
        if not years and text!=year_text:years=re.findall(r'\b20\d{2}\b',text)
        year=int(years[-1] if years else today.year)
        month=int(match.group(1))
    from .reports_service import operating_report
    from datetime import date
    start=date(year,month,1)
    end=date(year+1,1,1) if month==12 else date(year,month+1,1)
    report=operating_report(db,start,end)
    return {'ky_bao_cao_thang':{
        'bat_dau':str(start),'ket_thuc_khong_bao_gom':str(end),'nam_mac_dinh_neu_khach_khong_neu':year,
        'cong_suat_theo_lich_phan_tram':report['occupancy'],
        'dem_phong_phan_bo':report['allocated_nights'],
        'lich_luu_tru':report['booking_count'],
        'hoa_don_phat_hanh':str(report['invoice_gross']),
        'dieu_chinh_huy_no_show':str(report['adjustments']),
        'doanh_thu_hoa_don_rong':str(report['invoice_net']),
        'thu_tien_rong':str(report['net_cash']),
        'hoan_tien':str(report['refunded']),
        'ghi_chu':'Đơn vị tiền là VND. Doanh thu hóa đơn và dòng tiền được tổng hợp theo mốc thời gian riêng.'}}


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
    return await generate_content(contents, system, temperature=0.65)


def chatbot_context(db:Session,user=None)->dict:
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
            Booking.check_in == hotel_today(), Booking.status == BookingStatus.confirmed
        )
    ) or 0
    outstanding = db.scalar(
        select(func.coalesce(func.sum(case((Invoice.total+func.coalesce(FinancialAdjustment.amount,0)>Invoice.paid_amount,Invoice.total+func.coalesce(FinancialAdjustment.amount,0)-Invoice.paid_amount),else_=0)),0)).outerjoin(FinancialAdjustment,FinancialAdjustment.booking_id==Invoice.booking_id)
    ) or 0
    policy=db.get(HotelPolicy,1)
    result = {
        "ngay_hien_tai": str(hotel_today()),
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
        "quy_dinh_gio_khach_san": {
            "nhan_phong_tu_gio":policy.check_in_hour if policy else 14,
            "tra_phong_truoc_gio":policy.check_out_hour if policy else 12,
            "xu_ly_no_show_tu_gio":policy.no_show_hour if policy else 23,
            "phu_thu_nhan_phong_som":float(policy.early_fee) if policy else 0,
            "phu_thu_tra_phong_muon":float(policy.late_fee) if policy else 0,
            "phi_huy_phan_tram":float(policy.cancellation_percent) if policy else 0,
            "phi_khach_khong_den_phan_tram":float(policy.no_show_percent) if policy else 0,
        },
        "quy_trinh_he_thong": [
            "Kiểm tra ngày lưu trú, sức chứa và tình trạng phòng trước khi xác nhận đặt phòng.",
            "Lễ tân nhận phòng từ giờ quy định và chuyển đặt phòng sang trạng thái đang lưu trú.",
            "Khi trả phòng, ghi nhận dịch vụ phát sinh, lập hóa đơn và cập nhật khoản thu/hoàn theo giao dịch.",
        ],
        "tong_tien_con_phai_thu": float(outstanding),
    }
    if user is None or user.role not in (Role.admin,Role.accountant):result.pop('tong_tien_con_phai_thu',None)
    return result


async def hotel_chat(db:Session,messages,user=None)->str:
    latest=messages[-1].content if messages else ''
    customer_reply=_customer_lookup_reply(db,latest,user)
    if customer_reply:return customer_reply
    safe_messages=[]
    skip_customer_reply=False
    for message in messages[-12:]:
        if message.role=='user' and _is_customer_lookup(message.content):
            skip_customer_reply=True
            continue
        if message.role=='assistant' and skip_customer_reply:
            skip_customer_reply=False
            continue
        skip_customer_reply=False
        safe_messages.append({"role":message.role,"content":message.content})
    context=chatbot_context(db,user)
    recent_questions=' '.join(message.content for message in messages[-6:] if message.role=='user')
    report_context=_month_report_context(db,latest,user,recent_questions)
    if report_context:context.update(report_context)
    return await generate_chat(safe_messages,context)


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
    from .room_advice import advise
    return await advise(db,data)


async def booking_email(db: Session, booking_id: int, kind: str) -> str:
    from .email_service import draft_email
    content,_=await draft_email(db,booking_id,kind)
    return content


async def ai_report(db: Session) -> str:
    from .ai_reports import draft_report
    from core.hotel_time import hotel_today
    from datetime import timedelta
    today=hotel_today()
    content,_=await draft_report(db,today.replace(day=1),today+timedelta(days=1))
    return content
