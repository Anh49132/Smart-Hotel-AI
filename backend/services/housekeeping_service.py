from datetime import datetime
from fastapi import HTTPException
from sqlalchemy import select
from backend.models import CleaningTask, Booking, BookingStatus, Room, RoomStatus, User, Role
from .transactions import lock_room, write_transaction


def open_task(db, room_id):
    return db.scalar(select(CleaningTask).where(CleaningTask.room_id==room_id,CleaningTask.status!='ready').order_by(CleaningTask.id))


def create_cleaning_task(db,room_id):
    task=open_task(db,room_id)
    if not task:
        task=CleaningTask(room_id=room_id,status='pending')
        db.add(task)
    return task


def list_tasks(db,user):
    query=select(CleaningTask,Room.number).join(Room,Room.id==CleaningTask.room_id)
    if user.role==Role.housekeeping: query=query.where(CleaningTask.assigned_to==user.id,CleaningTask.status!='ready')
    rows=db.execute(query.order_by(CleaningTask.created_at.desc()).limit(200)).all()
    return [{'id':t.id,'room_id':t.room_id,'room':number,'assigned_to':t.assigned_to,'status':t.status,
             'created_at':t.created_at.isoformat(),'completed_at':t.completed_at.isoformat() if t.completed_at else None,
             'inspected_at':t.inspected_at.isoformat() if t.inspected_at else None} for t,number in rows]


def task_action(db,task_id,action,user,assigned_to=None):
    with write_transaction(db):
        room_id=db.scalar(select(CleaningTask.room_id).where(CleaningTask.id==task_id))
        if room_id is None: raise HTTPException(404,'Không tìm thấy việc dọn phòng')
        room=lock_room(db,room_id)
        task=db.scalar(select(CleaningTask).where(CleaningTask.id==task_id).with_for_update().execution_options(populate_existing=True))
        supervisor=user.role in (Role.admin,Role.receptionist)
        if not supervisor and task.assigned_to!=user.id: raise HTTPException(403,'Chỉ thao tác việc được phân công')
        now=datetime.utcnow()
        if action=='assign':
            if not supervisor: raise HTTPException(403,'Không có quyền phân công')
            assignee=db.get(User,assigned_to) if assigned_to else None
            if not assignee or not assignee.is_active or assignee.role!=Role.housekeeping: raise HTTPException(422,'Chọn nhân viên buồng phòng đang hoạt động')
            if task.status=='ready': raise HTTPException(409,'Việc đã hoàn tất')
            task.assigned_to=assignee.id
        elif action=='start' and task.status=='pending':
            task.status='in_progress';task.started_at=now
        elif action=='complete' and task.status=='in_progress':
            task.status='inspection';task.completed_at=now
        elif action=='inspect' and task.status=='inspection':
            if not supervisor: raise HTTPException(403,'Lễ tân/quản trị viên cần kiểm tra phòng')
            if room.status in (RoomStatus.occupied,RoomStatus.maintenance) or db.scalar(select(Booking.id).where(Booking.room_id==room_id,Booking.status==BookingStatus.checked_in).limit(1)):
                raise HTTPException(409,'Phòng đang có khách hoặc bảo trì')
            task.status='ready';task.inspected_at=now;task.inspected_by=user.id;room.status=RoomStatus.available
        else: raise HTTPException(409,'Thao tác không phù hợp trạng thái việc dọn')
        db.commit()
    return {'ok':True}
