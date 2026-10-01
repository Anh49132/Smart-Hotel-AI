from backend.dependencies import require_roles
from backend.models import Role
from backend.schemas import CustomerIn
from backend.services.customers_service import add_customer as add_customer_service, customers as customers_service, delete_customer as delete_customer_service, update_customer as update_customer_service
from core.database import get_db
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

router = APIRouter()

@router.get("/customers")
def customers(db: Session = Depends(get_db)):
    return customers_service(db=db)


@router.post("/customers")
def add_customer(data: CustomerIn, db: Session = Depends(get_db), _=Depends(require_roles(Role.admin, Role.receptionist))):
    return add_customer_service(data=data, db=db)


@router.put("/customers/{customer_id}")
def update_customer(customer_id: int, data: CustomerIn, db: Session = Depends(get_db), _=Depends(require_roles(Role.admin, Role.receptionist))):
    return update_customer_service(customer_id=customer_id, data=data, db=db)


@router.delete("/customers/{customer_id}")
def delete_customer(customer_id: int, db: Session = Depends(get_db), _=Depends(require_roles(Role.admin))):
    return delete_customer_service(customer_id=customer_id, db=db)
