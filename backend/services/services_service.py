from backend.models import Booking, BookingStatus, HotelService, ServiceUsage
from backend.schemas import ServiceIn, ServiceUsageIn
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

def services(db: Session):
    return db.scalars(select(HotelService)).all()

def add_service(data: ServiceIn, db: Session):
    item = HotelService(**data.model_dump())
    db.add(item)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, 'Tên dịch vụ đã tồn tại')
    db.refresh(item)
    return item

def update_service(service_id: int, data: ServiceIn, db: Session):
    item = db.get(HotelService, service_id)
    if not item:
        raise HTTPException(404, 'Không tìm thấy dịch vụ')
    for key, value in data.model_dump().items():
        setattr(item, key, value)
    db.commit()
    return {'ok': True}

def delete_service(service_id: int, db: Session):
    item = db.get(HotelService, service_id)
    if not item:
        raise HTTPException(404, 'Không tìm thấy dịch vụ')
    db.delete(item)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, 'Dịch vụ đã phát sinh trong lưu trú, hãy chuyển sang ngừng hoạt động')
    return {'ok': True}

def use_service(data: ServiceUsageIn, db: Session):
    service = db.get(HotelService, data.service_id)
    booking = db.get(Booking, data.booking_id)
    if not service or not booking:
        raise HTTPException(404, 'Không tìm thấy dịch vụ hoặc đặt phòng')
    if not service.active:
        raise HTTPException(409, 'Dịch vụ đã ngừng hoạt động')
    if booking.status != BookingStatus.checked_in:
        raise HTTPException(409, 'Chỉ ghi dịch vụ cho khách đang lưu trú')
    item = ServiceUsage(**data.model_dump(), unit_price=service.price)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def services(db: Session):
    return db.scalars(select(HotelService)).all()

def add_service(data: ServiceIn, db: Session):
    item = HotelService(**data.model_dump())
    db.add(item)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, 'Tên dịch vụ đã tồn tại')
    db.refresh(item)
    return item

def update_service(service_id: int, data: ServiceIn, db: Session):
    item = db.get(HotelService, service_id)
    if not item:
        raise HTTPException(404, 'Không tìm thấy dịch vụ')
    for key, value in data.model_dump().items():
        setattr(item, key, value)
    db.commit()
    return {'ok': True}

def delete_service(service_id: int, db: Session):
    item = db.get(HotelService, service_id)
    if not item:
        raise HTTPException(404, 'Không tìm thấy dịch vụ')
    db.delete(item)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, 'Dịch vụ đã phát sinh trong lưu trú, hãy chuyển sang ngừng hoạt động')
    return {'ok': True}

def use_service(data: ServiceUsageIn, db: Session):
    service = db.get(HotelService, data.service_id)
    booking = db.get(Booking, data.booking_id)
    if not service or not booking:
        raise HTTPException(404, 'Không tìm thấy dịch vụ hoặc đặt phòng')
    if not service.active:
        raise HTTPException(409, 'Dịch vụ đã ngừng hoạt động')
    if booking.status != BookingStatus.checked_in:
        raise HTTPException(409, 'Chỉ ghi dịch vụ cho khách đang lưu trú')
    item = ServiceUsage(**data.model_dump(), unit_price=service.price)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item
