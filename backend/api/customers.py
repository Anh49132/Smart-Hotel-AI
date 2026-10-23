from backend.dependencies import require_roles,get_current_user
from backend.models import Role,Customer
from backend.services.customers_service import customer_detail
from backend.schemas import CustomerIn
from backend.services.customers_service import add_customer as add_customer_service, customers as customers_service, delete_customer as delete_customer_service, update_customer as update_customer_service
from core.database import get_db
from fastapi import APIRouter, Depends,Query,HTTPException,Response
from sqlalchemy.orm import Session

router = APIRouter()

@router.get("/customers")
def customers(q:str=Query('',max_length=100),page:int=Query(1,ge=1),db: Session = Depends(get_db),user=Depends(get_current_user)):
    return customers_service(db=db,q=q,page=page,private=user.role in (Role.admin,Role.receptionist))


@router.get('/customers/{customer_id}')
def detail(customer_id:int,page:int=Query(1,ge=1),db:Session=Depends(get_db),user=Depends(get_current_user)):
    return customer_detail(db,customer_id,user.role in (Role.admin,Role.receptionist),page)


@router.get('/customers/{customer_id}/identity')
def reveal_identity(customer_id:int,response:Response,db:Session=Depends(get_db),user=Depends(require_roles(Role.admin,Role.receptionist))):
    item=db.get(Customer,customer_id)
    if not item:raise HTTPException(404,'Không tìm thấy khách hàng')
    response.headers['Cache-Control']='no-store'
    return {'identity_number':item.identity_number}


@router.post("/customers")
def add_customer(data: CustomerIn, db: Session = Depends(get_db), _=Depends(require_roles(Role.admin, Role.receptionist))):
    return add_customer_service(data=data, db=db)


@router.put("/customers/{customer_id}")
def update_customer(customer_id: int, data: CustomerIn, db: Session = Depends(get_db), _=Depends(require_roles(Role.admin, Role.receptionist))):
    return update_customer_service(customer_id=customer_id, data=data, db=db)


@router.delete("/customers/{customer_id}")
def delete_customer(customer_id: int, db: Session = Depends(get_db), _=Depends(require_roles(Role.admin))):
    return delete_customer_service(customer_id=customer_id, db=db)
