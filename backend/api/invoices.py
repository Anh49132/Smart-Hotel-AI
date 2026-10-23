from backend.dependencies import require_roles
from backend.models import Invoice, Payment, Role
from backend.schemas import PaymentIn
from backend.services.invoice_service import invoice as invoice_service, pay as pay_service
from core.database import get_db
from decimal import Decimal
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import select
from fastapi import HTTPException

router = APIRouter()

@router.post("/invoices/{booking_id}/calculate")
def invoice(booking_id: int, discount: Decimal = Decimal(0), db: Session = Depends(get_db), _=Depends(require_roles(Role.admin, Role.accountant))):
    return invoice_service(booking_id=booking_id, discount=discount, db=db)


@router.post("/invoices/{invoice_id}/payments")
def pay(invoice_id: int, data: PaymentIn, db: Session = Depends(get_db), user=Depends(require_roles(Role.admin, Role.accountant))):
    return pay_service(invoice_id=invoice_id, data=data, db=db, actor_id=user.id)


@router.get("/invoices/{invoice_id}/payments")
def payment_history(invoice_id: int, db: Session = Depends(get_db), _=Depends(require_roles(Role.admin, Role.accountant))):
    if not db.get(Invoice, invoice_id):
        raise HTTPException(404, "Không tìm thấy hóa đơn")
    return db.scalars(select(Payment).where(Payment.invoice_id == invoice_id).order_by(Payment.id)).all()
