from datetime import date
from decimal import Decimal
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload
from ..ai_service import advise_rooms, ai_report, booking_email, hotel_chat
from ..auth import get_current_user, require_roles
from ..database import get_db
from ..models import Booking, BookingStatus, Customer, HotelService, Invoice, Role, Room, RoomStatus, RoomType, ServiceUsage, User
from ..schemas import BookingIn, ChatRequest, CustomerIn, EmailRequest, PaymentIn, RoomAdviceIn, RoomIn, RoomTypeIn, ServiceIn, ServiceUsageIn, UserCreate
from ..services import calculate_invoice, create_booking, register_payment
from ..auth import hash_password


router = APIRouter(prefix="/api", dependencies=[Depends(get_current_user)])


@router.get("/rooms")
def list_rooms(check_in: Optional[date] = None, check_out: Optional[date] = None, guests: int = 1, db: Session = Depends(get_db)):
    query = select(Room).options(selectinload(Room.room_type)).join(RoomType).order_by(Room.number)
    if check_in and check_out:
        if check_out <= check_in:
            raise HTTPException(422, "Ngày trả phải sau ngày nhận")
        blocked = select(Booking.room_id).where(
            Booking.status.in_((BookingStatus.confirmed, BookingStatus.checked_in)),
            Booking.check_in < check_out,
            check_in < Booking.check_out,
        )
        query = query.where(Room.id.not_in(blocked), Room.status != RoomStatus.maintenance, RoomType.capacity >= guests)
    rooms = db.scalars(query).all()
    return [{"id": r.id, "number": r.number, "floor": r.floor, "status": r.status.value, "room_type": {"id": r.room_type.id, "name": r.room_type.name, "capacity": r.room_type.capacity, "nightly_rate": float(r.room_type.nightly_rate)}} for r in rooms]


@router.post("/room-types")
def add_room_type(data: RoomTypeIn, db: Session = Depends(get_db), _=Depends(require_roles(Role.admin))):
    item = RoomType(**data.model_dump()); db.add(item)
    try: db.commit()
    except IntegrityError: db.rollback(); raise HTTPException(409, "Tên loại phòng đã tồn tại")
    db.refresh(item); return item


@router.post("/rooms")
def add_room(data: RoomIn, db: Session = Depends(get_db), _=Depends(require_roles(Role.admin, Role.receptionist))):
    if not db.get(RoomType, data.room_type_id): raise HTTPException(404, "Không tìm thấy loại phòng")
    item = Room(**data.model_dump()); db.add(item)
    try: db.commit()
    except IntegrityError: db.rollback(); raise HTTPException(409, "Số phòng đã tồn tại")
    db.refresh(item); return item


@router.put("/rooms/{room_id}")
def update_room(room_id: int, data: RoomIn, db: Session = Depends(get_db), _=Depends(require_roles(Role.admin, Role.receptionist))):
    room = db.get(Room, room_id)
    if not room: raise HTTPException(404, "Không tìm thấy phòng")
    for key, value in data.model_dump().items(): setattr(room, key, value)
    try: db.commit()
    except IntegrityError: db.rollback(); raise HTTPException(409, "Số phòng đã tồn tại")
    return {"ok": True}


@router.delete("/rooms/{room_id}")
def delete_room(room_id: int, db: Session = Depends(get_db), _=Depends(require_roles(Role.admin))):
    room = db.get(Room, room_id)
    if not room: raise HTTPException(404, "Không tìm thấy phòng")
    db.delete(room)
    try: db.commit()
    except IntegrityError: db.rollback(); raise HTTPException(409, "Phòng đã có lịch sử đặt, không thể xóa")
    return {"ok": True}


@router.patch("/rooms/{room_id}/status")
def room_status(room_id: int, status: RoomStatus, db: Session = Depends(get_db), _=Depends(require_roles(Role.admin, Role.receptionist))):
    room = db.get(Room, room_id)
    if not room: raise HTTPException(404, "Không tìm thấy phòng")
    room.status = status; db.commit(); return {"ok": True}


@router.get("/customers")
def customers(db: Session = Depends(get_db)):
    return db.scalars(select(Customer).order_by(Customer.full_name)).all()


@router.post("/customers")
def add_customer(data: CustomerIn, db: Session = Depends(get_db), _=Depends(require_roles(Role.admin, Role.receptionist))):
    item = Customer(**data.model_dump()); db.add(item); db.commit(); db.refresh(item); return item


@router.put("/customers/{customer_id}")
def update_customer(customer_id: int, data: CustomerIn, db: Session = Depends(get_db), _=Depends(require_roles(Role.admin, Role.receptionist))):
    item = db.get(Customer, customer_id)
    if not item: raise HTTPException(404, "Không tìm thấy khách hàng")
    for key, value in data.model_dump().items(): setattr(item, key, value)
    db.commit(); return {"ok": True}


@router.delete("/customers/{customer_id}")
def delete_customer(customer_id: int, db: Session = Depends(get_db), _=Depends(require_roles(Role.admin))):
    item = db.get(Customer, customer_id)
    if not item: raise HTTPException(404, "Không tìm thấy khách hàng")
    db.delete(item)
    try: db.commit()
    except IntegrityError: db.rollback(); raise HTTPException(409, "Khách hàng đã có lịch sử lưu trú, không thể xóa")
    return {"ok": True}


@router.get("/bookings")
def bookings(db: Session = Depends(get_db)):
    return db.scalars(select(Booking).options(selectinload(Booking.customer), selectinload(Booking.room)).order_by(Booking.created_at.desc())).all()


@router.post("/bookings")
def add_booking(data: BookingIn, db: Session = Depends(get_db), _=Depends(require_roles(Role.admin, Role.receptionist))):
    return create_booking(db, data)


@router.post("/bookings/{booking_id}/{action}")
def booking_action(booking_id: int, action: str, db: Session = Depends(get_db), _=Depends(require_roles(Role.admin, Role.receptionist))):
    booking = db.get(Booking, booking_id)
    if not booking: raise HTTPException(404, "Không tìm thấy đặt phòng")
    transitions = {"check-in": (BookingStatus.confirmed, BookingStatus.checked_in, RoomStatus.occupied), "check-out": (BookingStatus.checked_in, BookingStatus.checked_out, RoomStatus.cleaning), "cancel": (BookingStatus.confirmed, BookingStatus.cancelled, RoomStatus.available)}
    if action not in transitions: raise HTTPException(400, "Thao tác không hợp lệ")
    expected, target, room_status = transitions[action]
    if booking.status != expected: raise HTTPException(409, "Trạng thái đặt phòng không phù hợp")
    booking.status, booking.room.status = target, room_status; db.commit()
    if action == "check-out": calculate_invoice(db, booking)
    return {"ok": True, "status": target}


@router.get("/services")
def services(db: Session = Depends(get_db)): return db.scalars(select(HotelService)).all()


@router.post("/services")
def add_service(data: ServiceIn, db: Session = Depends(get_db), _=Depends(require_roles(Role.admin))):
    item = HotelService(**data.model_dump()); db.add(item)
    try: db.commit()
    except IntegrityError: db.rollback(); raise HTTPException(409, "Tên dịch vụ đã tồn tại")
    db.refresh(item); return item


@router.put("/services/{service_id}")
def update_service(service_id: int, data: ServiceIn, db: Session = Depends(get_db), _=Depends(require_roles(Role.admin))):
    item = db.get(HotelService, service_id)
    if not item: raise HTTPException(404, "Không tìm thấy dịch vụ")
    for key, value in data.model_dump().items(): setattr(item, key, value)
    db.commit(); return {"ok": True}


@router.delete("/services/{service_id}")
def delete_service(service_id: int, db: Session = Depends(get_db), _=Depends(require_roles(Role.admin))):
    item = db.get(HotelService, service_id)
    if not item: raise HTTPException(404, "Không tìm thấy dịch vụ")
    db.delete(item)
    try: db.commit()
    except IntegrityError: db.rollback(); raise HTTPException(409, "Dịch vụ đã phát sinh trong lưu trú, hãy chuyển sang ngừng hoạt động")
    return {"ok": True}


@router.post("/service-usages")
def use_service(data: ServiceUsageIn, db: Session = Depends(get_db), _=Depends(require_roles(Role.admin, Role.receptionist))):
    service = db.get(HotelService, data.service_id)
    booking = db.get(Booking, data.booking_id)
    if not service or not booking: raise HTTPException(404, "Không tìm thấy dịch vụ hoặc đặt phòng")
    if not service.active: raise HTTPException(409, "Dịch vụ đã ngừng hoạt động")
    if booking.status != BookingStatus.checked_in: raise HTTPException(409, "Chỉ ghi dịch vụ cho khách đang lưu trú")
    item = ServiceUsage(**data.model_dump(), unit_price=service.price); db.add(item); db.commit(); db.refresh(item); return item


@router.post("/invoices/{booking_id}/calculate")
def invoice(booking_id: int, discount: Decimal = Decimal(0), db: Session = Depends(get_db), _=Depends(require_roles(Role.admin, Role.accountant))):
    booking = db.get(Booking, booking_id)
    if not booking: raise HTTPException(404, "Không tìm thấy đặt phòng")
    return calculate_invoice(db, booking, discount)


@router.post("/invoices/{invoice_id}/payments")
def pay(invoice_id: int, data: PaymentIn, db: Session = Depends(get_db), _=Depends(require_roles(Role.admin, Role.accountant))):
    item = db.get(Invoice, invoice_id)
    if not item: raise HTTPException(404, "Không tìm thấy hóa đơn")
    return register_payment(db, item, data.amount)


@router.post("/ai/room-advice")
async def room_advice(data: RoomAdviceIn, db: Session = Depends(get_db)): return await advise_rooms(db, data)


@router.post("/ai/email")
async def email(data: EmailRequest, db: Session = Depends(get_db)): return {"content": await booking_email(db, data.booking_id, data.kind)}


@router.get("/ai/report")
async def report(db: Session = Depends(get_db)): return {"content": await ai_report(db)}


@router.post("/ai/chat")
async def chat(data: ChatRequest, db: Session = Depends(get_db)):
    return {"content": await hotel_chat(db, data.messages)}


@router.post("/users")
def add_user(data: UserCreate, db: Session = Depends(get_db), _=Depends(require_roles(Role.admin))):
    item = User(username=data.username, full_name=data.full_name, role=data.role, password_hash=hash_password(data.password)); db.add(item)
    try: db.commit()
    except IntegrityError: db.rollback(); raise HTTPException(409, "Tên đăng nhập đã tồn tại")
    db.refresh(item); return {"id": item.id}


@router.get("/users")
def list_users(db: Session = Depends(get_db), _=Depends(require_roles(Role.admin))):
    return [{"id": u.id, "username": u.username, "full_name": u.full_name, "role": u.role.value, "is_active": u.is_active} for u in db.scalars(select(User).order_by(User.full_name)).all()]


@router.patch("/users/{user_id}/active")
def toggle_user(user_id: int, active: bool, db: Session = Depends(get_db), current=Depends(require_roles(Role.admin))):
    item = db.get(User, user_id)
    if not item: raise HTTPException(404, "Không tìm thấy tài khoản")
    if item.id == current.id and not active: raise HTTPException(409, "Không thể tự khóa tài khoản đang đăng nhập")
    item.is_active = active; db.commit(); return {"ok": True}
