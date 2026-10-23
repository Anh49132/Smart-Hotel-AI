from datetime import datetime
from fastapi import HTTPException
from sqlalchemy import select
from backend.models import RoomBlock,Room,User,Role,RoomStatus
from .transactions import lock_room,write_transaction
from .inventory_service import room_available
from .housekeeping_service import create_cleaning_task


def create_block(db,data,user):
    with write_transaction(db):
        room=lock_room(db,data.room_id)
        if not room: raise HTTPException(404,'Không tìm thấy phòng')
        if not room_available(db,room.id,data.start_date,data.end_date):
            raise HTTPException(409,'Khoảng bảo trì trùng đặt phòng hoặc khóa bán hiện có; cần xử lý lịch trước')
        if data.assigned_to:
            assignee=db.get(User,data.assigned_to)
            if not assignee or not assignee.is_active or assignee.role not in (Role.admin,Role.receptionist):
                raise HTTPException(422,'Người phụ trách phải là quản trị viên/lễ tân đang hoạt động')
        item=RoomBlock(**data.model_dump(),created_by=user.id)
        db.add(item);db.commit();db.refresh(item)
        return {'id':item.id}


def update_block(db,block_id,status,user):
    with write_transaction(db):
        room_id=db.scalar(select(RoomBlock.room_id).where(RoomBlock.id==block_id))
        if room_id is None: raise HTTPException(404,'Không tìm thấy phiếu bảo trì')
        room=lock_room(db,room_id)
        item=db.scalar(select(RoomBlock).where(RoomBlock.id==block_id).with_for_update().execution_options(populate_existing=True))
        if item.status in ('resolved','cancelled') or status not in ('in_progress','resolved','cancelled') or status==item.status:
            raise HTTPException(409,'Chuyển trạng thái phiếu không hợp lệ')
        item.status=status
        if status in ('resolved','cancelled'): item.resolved_at=datetime.utcnow()
        if status=='resolved' and room.status==RoomStatus.maintenance:
            room.status=RoomStatus.cleaning
            create_cleaning_task(db,room_id)
        db.commit()
    return {'ok':True}


def blocks(db):
    rows=db.execute(select(RoomBlock,Room.number).join(Room,Room.id==RoomBlock.room_id).order_by(RoomBlock.created_at.desc()).limit(200)).all()
    return [{'id':b.id,'room':number,'room_id':b.room_id,'start_date':str(b.start_date),'end_date':str(b.end_date),
             'description':b.description,'status':b.status,'assigned_to':b.assigned_to,'resolved_at':b.resolved_at.isoformat() if b.resolved_at else None} for b,number in rows]
