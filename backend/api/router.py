from . import ai, bookings, customers, invoices, rooms, services, users
from backend.dependencies import get_current_user
from fastapi import APIRouter, Depends

router = APIRouter(prefix="/api", dependencies=[Depends(get_current_user)])
router.include_router(rooms.router)
router.include_router(customers.router)
router.include_router(bookings.router)
router.include_router(services.router)
router.include_router(invoices.router)
router.include_router(ai.router)
router.include_router(users.router)
