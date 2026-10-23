from backend.models import Booking, Customer
from backend.schemas import CustomerIn
from fastapi import HTTPException
from sqlalchemy import select, func, or_, case
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from datetime import timezone
from core.hotel_time import HOTEL_TIMEZONE

def mask_identity(value):
    if not value: return ''
    return '*'*max(4,len(value)-4)+(value[-4:] if len(value)>4 else '')


def customer_summary(item,private=False):
    return {'id':item.id,'full_name':item.full_name,'phone':item.phone,'email':item.email,
            'identity_masked':mask_identity(item.identity_number),'preference_notes':item.preference_notes if private else ''}


def customers(db: Session,q='',page=1,private=False):
    query=select(Customer)
    if q:
        query=query.where(or_(Customer.full_name.icontains(q,autoescape=True),Customer.phone.contains(q,autoescape=True),Customer.email.icontains(q,autoescape=True)))
    total=db.scalar(select(func.count()).select_from(query.subquery()))
    items=db.scalars(query.order_by(Customer.full_name,Customer.id).offset((page-1)*20).limit(20)).all()
    ids=[c.id for c in items]
    stats={row[0]:(row[1],row[2],row[3]) for row in db.execute(select(Booking.customer_id,func.count(Booking.id),func.max(Booking.actual_check_out),func.max(case((Booking.actual_check_out.is_(None),Booking.check_out),else_=None))).where(Booking.customer_id.in_(ids),Booking.status=='checked_out').group_by(Booking.customer_id))}
    result=[]
    for item in items:
        row=customer_summary(item,private)
        count,actual,legacy=stats.get(item.id,(0,None,None))
        dates=[d for d in (actual.replace(tzinfo=timezone.utc).astimezone(HOTEL_TIMEZONE).date() if actual else None,legacy) if d]
        row.update(completed_stays=count,last_stay=str(max(dates)) if dates else None)
        result.append(row)
    return {'items':result,'total':total,'page':page,'pages':max(1,(total+19)//20),'q':q}


def customer_detail(db,customer_id,private=False,page=1):
    item=db.get(Customer,customer_id)
    if not item:raise HTTPException(404,'Không tìm thấy khách hàng')
    counts=dict(db.execute(select(Booking.status,func.count(Booking.id)).where(Booking.customer_id==customer_id).group_by(Booking.status)).all())
    records=db.scalars(select(Booking).where(Booking.customer_id==customer_id).order_by(Booking.check_in.desc(),Booking.id.desc()).offset((page-1)*20).limit(20)).all()
    row=customer_summary(item,private)
    row.update(counts={status.value:count for status,count in counts.items()},history=[{'id':b.id,'code':b.code,'check_in':str(b.check_in),'check_out':str(b.check_out),'status':b.status.value,'room':b.room.number} for b in records],page=page,pages=max(1,(sum(counts.values())+19)//20))
    return row


def add_customer(data: CustomerIn, db: Session):
    item = Customer(**data.model_dump(exclude={'clear_identity'}))
    db.add(item)
    db.commit()
    db.refresh(item)
    return customer_summary(item,True)

def update_customer(customer_id: int, data: CustomerIn, db: Session):
    item = db.get(Customer, customer_id)
    if not item:
        raise HTTPException(404, 'Không tìm thấy khách hàng')
    values=data.model_dump(exclude={'clear_identity'})
    if 'preference_notes' not in data.model_fields_set: values.pop('preference_notes')
    if not data.identity_number and not data.clear_identity: values.pop('identity_number')
    if data.clear_identity: values['identity_number']=None
    for key, value in values.items():
        setattr(item, key, value)
    db.commit()
    return {'ok': True}

def delete_customer(customer_id: int, db: Session):
    item = db.get(Customer, customer_id)
    if not item:
        raise HTTPException(404, 'Không tìm thấy khách hàng')
    if db.scalar(select(Booking.id).where(Booking.customer_id == customer_id).limit(1)):
        raise HTTPException(409, 'Khách hàng đã có lịch sử lưu trú, không thể xóa')
    db.delete(item)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, 'Khách hàng đã có lịch sử lưu trú, không thể xóa')
    return {'ok': True}
