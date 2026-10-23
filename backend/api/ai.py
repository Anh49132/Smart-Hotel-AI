from backend.schemas import ChatRequest, EmailRequest, RoomAdviceIn
from backend.services.ai_service import advise_rooms, ai_report, booking_email, hotel_chat
from backend.dependencies import require_roles
from backend.models import AIResult, AIReviewEvent, Role
from backend.services.email_service import draft_email,EMAIL_VERSION
from backend.services.transactions import write_transaction
from core.config import settings
import json
from core.database import get_db
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select,update
from sqlalchemy.orm import Session

router = APIRouter()

@router.post("/ai/room-advice")
async def room_advice(data: RoomAdviceIn, db: Session = Depends(get_db), user=Depends(require_roles(Role.admin, Role.receptionist))):
    result = await advise_rooms(db, data)
    if result["rooms"]:
        record = AIResult(kind="room_advice", content=result["message"], generated_by=user.id)
        db.add(record); db.commit(); db.refresh(record)
        result["ai_result_id"] = record.id
    return result


@router.post("/ai/email")
async def email(data: EmailRequest, db: Session = Depends(get_db), user=Depends(require_roles(Role.admin, Role.receptionist))):
    content,facts = await draft_email(db,data.booking_id,data.kind)
    record = AIResult(kind="email",content=content,booking_id=data.booking_id,generated_by=user.id,email_kind=data.kind,model_name=settings.gemini_model,prompt_version=EMAIL_VERSION,source_json=json.dumps(facts,ensure_ascii=False))
    db.add(record); db.commit(); db.refresh(record)
    return {"content": content, "ai_result_id": record.id, "review_status": record.review_status}


@router.get("/ai/report")
async def report(db: Session = Depends(get_db), user=Depends(require_roles(Role.admin, Role.accountant))):
    content = await ai_report(db)
    record = AIResult(kind="report", content=content, generated_by=user.id)
    db.add(record); db.commit(); db.refresh(record)
    return {"content": content, "ai_result_id": record.id, "review_status": record.review_status}


@router.post("/ai/chat")
async def chat(data: ChatRequest, db: Session = Depends(get_db)):
    return {"content": await hotel_chat(db, data.messages)}


@router.get("/ai/results")
def ai_results(db: Session = Depends(get_db), user=Depends(require_roles(Role.admin,Role.accountant,Role.receptionist))):
    query=select(AIResult).order_by(AIResult.id.desc()).limit(100)
    if user.role==Role.receptionist:query=query.where(AIResult.generated_by==user.id,AIResult.kind.in_(('email','room_advice')))
    return db.scalars(query).all()


@router.post("/ai/results/{result_id}/review")
def review_ai_result(result_id: int, approved: bool, db: Session = Depends(get_db), user=Depends(require_roles(Role.admin, Role.accountant))):
    with write_transaction(db):
        if db.get_bind().dialect.name=='sqlite':db.execute(update(AIResult).where(AIResult.id==result_id).values(id=AIResult.id))
        record=db.scalar(select(AIResult).where(AIResult.id==result_id).with_for_update().execution_options(populate_existing=True))
        if not record:raise HTTPException(404,'Không tìm thấy kết quả AI')
        if record.review_status!='pending':raise HTTPException(409,'Kết quả AI đã được duyệt')
        record.review_status='approved' if approved else 'rejected';record.reviewed_by=user.id;record.reviewed_at=datetime.utcnow()
        db.add(AIReviewEvent(result_id=record.id,actor_id=user.id,approved=approved))
        db.commit();db.refresh(record)
    return record


@router.get('/ai/results/{result_id}')
def result_detail(result_id:int,db:Session=Depends(get_db),user=Depends(require_roles(Role.admin,Role.accountant,Role.receptionist))):
    record=db.get(AIResult,result_id)
    if not record:raise HTTPException(404,'Không tìm thấy bản nháp')
    if user.role==Role.receptionist and (record.generated_by!=user.id or record.kind not in ('email','room_advice')):raise HTTPException(403,'Chỉ xem bản nháp của chính mình')
    return {'id':record.id,'kind':record.kind,'email_kind':record.email_kind,'content':record.content,'review_status':record.review_status,'model':record.model_name,'prompt_version':record.prompt_version,'source':json.loads(record.source_json),'reviews':[{'actor_id':e.actor_id,'approved':e.approved,'at':e.created_at.isoformat()} for e in db.scalars(select(AIReviewEvent).where(AIReviewEvent.result_id==result_id))]}
