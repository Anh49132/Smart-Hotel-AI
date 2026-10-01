from backend.models import Customer
from backend.schemas import CustomerIn
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

def customers(db: Session):
    return db.scalars(select(Customer).order_by(Customer.full_name)).all()

def add_customer(data: CustomerIn, db: Session):
    item = Customer(**data.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item

def update_customer(customer_id: int, data: CustomerIn, db: Session):
    item = db.get(Customer, customer_id)
    if not item:
        raise HTTPException(404, 'Không tìm thấy khách hàng')
    for key, value in data.model_dump().items():
        setattr(item, key, value)
    db.commit()
    return {'ok': True}

def delete_customer(customer_id: int, db: Session):
    item = db.get(Customer, customer_id)
    if not item:
        raise HTTPException(404, 'Không tìm thấy khách hàng')
    db.delete(item)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, 'Khách hàng đã có lịch sử lưu trú, không thể xóa')
    return {'ok': True}


def customers(db: Session):
    return db.scalars(select(Customer).order_by(Customer.full_name)).all()

def add_customer(data: CustomerIn, db: Session):
    item = Customer(**data.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item

def update_customer(customer_id: int, data: CustomerIn, db: Session):
    item = db.get(Customer, customer_id)
    if not item:
        raise HTTPException(404, 'Không tìm thấy khách hàng')
    for key, value in data.model_dump().items():
        setattr(item, key, value)
    db.commit()
    return {'ok': True}

def delete_customer(customer_id: int, db: Session):
    item = db.get(Customer, customer_id)
    if not item:
        raise HTTPException(404, 'Không tìm thấy khách hàng')
    db.delete(item)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, 'Khách hàng đã có lịch sử lưu trú, không thể xóa')
    return {'ok': True}
