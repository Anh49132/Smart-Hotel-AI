"""Whitelist API fields so ORM relationships cannot leak guest identity data."""
from datetime import date,datetime
from decimal import Decimal
from pydantic import BaseModel,ConfigDict


class BookingOut(BaseModel):
    model_config=ConfigDict(from_attributes=True)
    id:int
    code:str
    customer_id:int
    room_id:int
    check_in:date
    check_out:date
    guests:int
    status:str
    booked_nightly_rate:Decimal


class InvoiceOut(BaseModel):
    model_config=ConfigDict(from_attributes=True)
    id:int
    booking_id:int
    room_amount:Decimal
    service_amount:Decimal
    surcharge_amount:Decimal
    discount:Decimal
    total:Decimal
    paid_amount:Decimal
    payment_status:str
    issued_at:datetime
    effective_total:Decimal|None=None
    balance_due:Decimal|None=None
