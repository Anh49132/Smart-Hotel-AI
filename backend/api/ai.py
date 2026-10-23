from backend.schemas import ChatRequest, EmailRequest, RoomAdviceIn
from backend.services.ai_service import advise_rooms, ai_report, booking_email, hotel_chat
from backend.dependencies import require_roles
from backend.models import AIResult, Role
from core.database import get_db
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
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
    content = await booking_email(db, data.booking_id, data.kind)
    record = AIResult(kind="email", content=content, booking_id=data.booking_id, generated_by=user.id)
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
def ai_results(db: Session = Depends(get_db), _=Depends(require_roles(Role.admin, Role.accountant))):
    return db.scalars(select(AIResult).order_by(AIResult.id.desc()).limit(100)).all()


@router.post("/ai/results/{result_id}/review")
def review_ai_result(result_id: int, approved: bool, db: Session = Depends(get_db), user=Depends(require_roles(Role.admin, Role.accountant))):
    record = db.get(AIResult, result_id)
    if not record:
        raise HTTPException(404, "Không tìm thấy kết quả AI")
    if record.review_status != "pending":
        raise HTTPException(409, "Kết quả AI đã được duyệt")
    record.review_status = "approved" if approved else "rejected"
    record.reviewed_by = user.id
    record.reviewed_at = datetime.utcnow()
    db.commit(); db.refresh(record)
    return record
