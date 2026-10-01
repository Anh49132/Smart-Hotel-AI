from backend.schemas import ChatRequest, EmailRequest, RoomAdviceIn
from backend.services.ai_service import advise_rooms, ai_report, booking_email, hotel_chat
from core.database import get_db
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

router = APIRouter()

@router.post("/ai/room-advice")
async def room_advice(data: RoomAdviceIn, db: Session = Depends(get_db)): return await advise_rooms(db, data)


@router.post("/ai/email")
async def email(data: EmailRequest, db: Session = Depends(get_db)): return {"content": await booking_email(db, data.booking_id, data.kind)}


@router.get("/ai/report")
async def report(db: Session = Depends(get_db)): return {"content": await ai_report(db)}


@router.post("/ai/chat")
async def chat(data: ChatRequest, db: Session = Depends(get_db)):
    return {"content": await hotel_chat(db, data.messages)}
