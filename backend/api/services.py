from backend.dependencies import require_roles
from backend.models import Role
from backend.schemas import ServiceIn, ServiceUsageIn
from backend.services.services_service import add_service as add_service_service, delete_service as delete_service_service, services as services_service, update_service as update_service_service, use_service as use_service_service
from core.database import get_db
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

router = APIRouter()

@router.get("/services")
def services(db: Session = Depends(get_db)):
    return services_service(db=db)


@router.post("/services")
def add_service(data: ServiceIn, db: Session = Depends(get_db), _=Depends(require_roles(Role.admin))):
    return add_service_service(data=data, db=db)


@router.put("/services/{service_id}")
def update_service(service_id: int, data: ServiceIn, db: Session = Depends(get_db), _=Depends(require_roles(Role.admin))):
    return update_service_service(service_id=service_id, data=data, db=db)


@router.delete("/services/{service_id}")
def delete_service(service_id: int, db: Session = Depends(get_db), _=Depends(require_roles(Role.admin))):
    return delete_service_service(service_id=service_id, db=db)


@router.post("/service-usages")
def use_service(data: ServiceUsageIn, db: Session = Depends(get_db), _=Depends(require_roles(Role.admin, Role.receptionist))):
    return use_service_service(data=data, db=db)
