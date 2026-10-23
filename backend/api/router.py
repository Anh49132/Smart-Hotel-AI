from . import ai, bookings, customers, invoices, rooms, services, users, housekeeping, maintenance, frontdesk
from backend.dependencies import get_current_user
from fastapi import APIRouter, Depends
from . import money

router = APIRouter(prefix="/api", dependencies=[Depends(get_current_user)])
router.include_router(rooms.router)
router.include_router(customers.router)
router.include_router(bookings.router)
router.include_router(services.router)
router.include_router(invoices.router)
router.include_router(ai.router)
router.include_router(users.router)
router.include_router(housekeeping.router)
router.include_router(maintenance.router)
router.include_router(frontdesk.router)
router.include_router(money.router)
