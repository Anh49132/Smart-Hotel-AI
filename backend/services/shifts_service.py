"""Cash drawer totals are derived from the immutable ledger, never client input."""
import json
from datetime import datetime
from decimal import Decimal
from fastapi import HTTPException
from sqlalchemy import select, update, func
from backend.models import CashierShift, MoneyEntry, User, Role, Booking, BookingStatus, CleaningTask
from .transactions import write_transaction


def current_shift(db, user_id, lock=False):
    if lock and db.get_bind().dialect.name=='sqlite':
        db.execute(update(CashierShift).where(CashierShift.cashier_id==user_id,CashierShift.status=='open').values(id=CashierShift.id))
    query=select(CashierShift).where(CashierShift.cashier_id==user_id,CashierShift.status=='open').execution_options(populate_existing=True)
    item=db.scalar(query.with_for_update() if lock else query)
    if lock and not item:raise HTTPException(409,'Hãy mở ca tại mục Ca thu ngân trước khi thu/hoàn tiền')
    return item


def totals(db,shift):
    result={method:{'in':Decimal(0),'out':Decimal(0)} for method in ('cash','bank_transfer')}
    for e in db.scalars(select(MoneyEntry).where(MoneyEntry.shift_id==shift.id)):
        result[e.method]['out' if e.kind=='refund' else 'in']+=e.amount
    result['expected_cash']=shift.opening_cash+result['cash']['in']-result['cash']['out']
    return result


def open_shift(db,user,opening_cash):
    with write_transaction(db):
        if db.get_bind().dialect.name=='sqlite':db.execute(update(User).where(User.id==user.id).values(id=User.id))
        db.scalar(select(User).where(User.id==user.id).with_for_update())
        if current_shift(db,user.id):raise HTTPException(409,'Bạn đã có ca đang mở')
        item=CashierShift(cashier_id=user.id,opening_cash=opening_cash)
        db.add(item);db.commit();db.refresh(item)
        return {'id':item.id}


def close_shift(db,shift_id,user,data):
    with write_transaction(db):
        if db.get_bind().dialect.name=='sqlite':db.execute(update(CashierShift).where(CashierShift.id==shift_id).values(id=CashierShift.id))
        item=db.scalar(select(CashierShift).where(CashierShift.id==shift_id).with_for_update().execution_options(populate_existing=True))
        if not item:raise HTTPException(404,'Không tìm thấy ca')
        if item.cashier_id!=user.id:raise HTTPException(403,'Chỉ được chốt ca của chính mình')
        if item.status!='open':raise HTTPException(409,'Ca đã chốt, không được sửa')
        if data.handed_to is not None:
            recipient=db.get(User,data.handed_to)
            if not recipient or not recipient.is_active or recipient.role not in (Role.admin,Role.receptionist,Role.accountant) or recipient.id==user.id:
                raise HTTPException(400,'Người nhận phải là thu ngân khác đang hoạt động')
        summary=totals(db,item)
        summary['pending']={'staying':db.scalar(select(func.count()).select_from(Booking).where(Booking.status==BookingStatus.checked_in)),'cleaning':db.scalar(select(func.count()).select_from(CleaningTask).where(CleaningTask.status!='ready'))}
        item.expected_cash=summary['expected_cash'];item.counted_cash=data.counted_cash
        item.difference=data.counted_cash-item.expected_cash
        item.handed_to=data.handed_to;item.note=data.note;item.closed_at=datetime.utcnow();item.status='closed'
        item.snapshot_json=json.dumps(summary,default=str,ensure_ascii=False)
        db.commit()
        return {'expected_cash':str(item.expected_cash),'difference':str(item.difference)}


def shift_view(db,item):
    snapshot=json.loads(item.snapshot_json) if item.status=='closed' else totals(db,item)
    return {'id':item.id,'cashier_id':item.cashier_id,'status':item.status,'opened_at':item.opened_at,'closed_at':item.closed_at,'opening_cash':item.opening_cash,'counted_cash':item.counted_cash,'difference':item.difference,'handed_to':item.handed_to,'note':item.note,'totals':snapshot}
