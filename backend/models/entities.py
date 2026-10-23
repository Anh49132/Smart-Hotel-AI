from core.database import Base
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, Enum as SQLEnum, ForeignKey, Index, Numeric, String, Text, UniqueConstraint, true, false, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

class Role(str, Enum):
    admin = "admin"
    receptionist = "receptionist"
    accountant = "accountant"
    housekeeping = "housekeeping"


class RoomStatus(str, Enum):
    available = "available"
    occupied = "occupied"
    cleaning = "cleaning"
    maintenance = "maintenance"


class BookingStatus(str, Enum):
    confirmed = "confirmed"
    checked_in = "checked_in"
    checked_out = "checked_out"
    cancelled = "cancelled"
    no_show = "no_show"


class PaymentStatus(str, Enum):
    unpaid = "unpaid"
    partial = "partial"
    paid = "paid"


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(120))
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[Role] = mapped_column(SQLEnum(Role))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    token_version: Mapped[int] = mapped_column(default=0, server_default="0")
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())


class RoomType(Base):
    __tablename__ = "room_types"
    __table_args__ = (CheckConstraint("capacity > 0", name="ck_room_type_capacity"), CheckConstraint("nightly_rate > 0", name="ck_room_type_rate"), CheckConstraint("weekend_rate IS NULL OR weekend_rate > 0", name="ck_room_type_weekend"))
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True)
    capacity: Mapped[int]
    nightly_rate: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    weekend_rate: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=true())
    amenities: Mapped[str] = mapped_column(Text, default="")
    rooms: Mapped[list["Room"]] = relationship(back_populates="room_type")


class RatePlan(Base):
    __tablename__ = 'rate_plans'
    __table_args__ = (CheckConstraint('end_date > start_date', name='ck_rate_plan_dates'), CheckConstraint('nightly_rate > 0', name='ck_rate_plan_price'))
    id: Mapped[int] = mapped_column(primary_key=True)
    room_type_id: Mapped[int] = mapped_column(ForeignKey('room_types.id'), index=True)
    name: Mapped[str] = mapped_column(String(100))
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    nightly_rate: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())


class Room(Base):
    __tablename__ = "rooms"
    id: Mapped[int] = mapped_column(primary_key=True)
    number: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    floor: Mapped[int]
    status: Mapped[RoomStatus] = mapped_column(SQLEnum(RoomStatus), default=RoomStatus.available)
    room_type_id: Mapped[int] = mapped_column(ForeignKey("room_types.id"))
    room_type: Mapped[RoomType] = relationship(back_populates="rooms")


class Customer(Base):
    __tablename__ = "customers"
    id: Mapped[int] = mapped_column(primary_key=True)
    full_name: Mapped[str] = mapped_column(String(120), index=True)
    phone: Mapped[str] = mapped_column(String(30))
    # Keep non-union annotations for SQLAlchemy 2.0.x compatibility on Python 3.14.
    # The database columns remain nullable and may still contain NULL at runtime.
    email: Mapped[str] = mapped_column(String(160), nullable=True)
    identity_number: Mapped[str] = mapped_column(String(80), nullable=True)
    preference_notes: Mapped[str] = mapped_column(Text,server_default='')
    bookings: Mapped[list["Booking"]] = relationship(back_populates="customer")


class Booking(Base):
    __tablename__ = "bookings"
    __table_args__ = (CheckConstraint("check_out > check_in", name="ck_booking_dates"), CheckConstraint("guests > 0", name="ck_booking_guests"), CheckConstraint('booked_nightly_rate >= 0', name='ck_booking_rate'), Index('ix_booking_overlap', 'room_id', 'status', 'check_in', 'check_out'))
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(24), unique=True, index=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"))
    room_id: Mapped[int] = mapped_column(ForeignKey("rooms.id"), index=True)
    check_in: Mapped[date] = mapped_column(Date, index=True)
    check_out: Mapped[date] = mapped_column(Date, index=True)
    guests: Mapped[int]
    booked_nightly_rate: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    booked_rate_source: Mapped[str] = mapped_column(String(24), server_default="confirmed")
    status: Mapped[BookingStatus] = mapped_column(SQLEnum(BookingStatus), default=BookingStatus.confirmed)
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    customer: Mapped[Customer] = relationship(back_populates="bookings")
    actual_check_in: Mapped[datetime] = mapped_column(DateTime,nullable=True)
    actual_check_out: Mapped[datetime] = mapped_column(DateTime,nullable=True)
    room: Mapped[Room] = relationship()
    service_usages: Mapped[list["ServiceUsage"]] = relationship(back_populates="booking", cascade="all, delete-orphan")
    invoice: Mapped["Invoice"] = relationship(back_populates="booking", uselist=False)
    status_history: Mapped[list["BookingStatusHistory"]] = relationship(back_populates="booking", order_by="BookingStatusHistory.changed_at")


class BookingNight(Base):
    __tablename__ = 'booking_nights'
    __table_args__ = (UniqueConstraint('booking_id', 'stay_date', name='uq_booking_night'), CheckConstraint('amount >= 0', name='ck_booking_night_amount'))
    id: Mapped[int] = mapped_column(primary_key=True)
    booking_id: Mapped[int] = mapped_column(ForeignKey('bookings.id'), index=True)
    stay_date: Mapped[date] = mapped_column(Date)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    source: Mapped[str] = mapped_column(String(120))


class RoomStay(Base):
    __tablename__ = 'room_stays'
    __table_args__ = (CheckConstraint('check_out > check_in', name='ck_stay_dates'), Index('ix_stay_overlap', 'room_id', 'check_in', 'check_out'))
    id: Mapped[int] = mapped_column(primary_key=True)
    booking_id: Mapped[int] = mapped_column(ForeignKey('bookings.id'), index=True)
    room_id: Mapped[int] = mapped_column(ForeignKey('rooms.id'))
    check_in: Mapped[date] = mapped_column(Date)
    check_out: Mapped[date] = mapped_column(Date)


class BookingChange(Base):
    __tablename__ = 'booking_changes'
    id: Mapped[int] = mapped_column(primary_key=True)
    booking_id: Mapped[int] = mapped_column(ForeignKey('bookings.id'), index=True)
    changed_by: Mapped[int] = mapped_column(ForeignKey('users.id'), nullable=True)
    reason: Mapped[str] = mapped_column(String(500))
    before_data: Mapped[str] = mapped_column(Text)
    after_data: Mapped[str] = mapped_column(Text)
    changed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class CleaningTask(Base):
    __tablename__ = 'cleaning_tasks'
    __table_args__ = (CheckConstraint("status IN ('pending','in_progress','inspection','ready')", name='ck_cleaning_status'),)
    id: Mapped[int] = mapped_column(primary_key=True)
    room_id: Mapped[int] = mapped_column(ForeignKey('rooms.id'), index=True)
    assigned_to: Mapped[int] = mapped_column(ForeignKey('users.id'), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default='pending')
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    inspected_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    inspected_by: Mapped[int] = mapped_column(ForeignKey('users.id'), nullable=True)


class RoomBlock(Base):
    __tablename__='room_blocks'
    __table_args__=(CheckConstraint('end_date > start_date',name='ck_block_dates'),CheckConstraint("status IN ('open','in_progress','resolved','cancelled')",name='ck_block_status'),Index('ix_block_overlap','room_id','start_date','end_date'))
    id: Mapped[int]=mapped_column(primary_key=True)
    room_id: Mapped[int]=mapped_column(ForeignKey('rooms.id'))
    start_date: Mapped[date]=mapped_column(Date)
    end_date: Mapped[date]=mapped_column(Date)
    description: Mapped[str]=mapped_column(String(500))
    status: Mapped[str]=mapped_column(String(20),default='open')
    assigned_to: Mapped[int]=mapped_column(ForeignKey('users.id'),nullable=True)
    created_by: Mapped[int]=mapped_column(ForeignKey('users.id'))
    created_at: Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)
    resolved_at: Mapped[datetime]=mapped_column(DateTime,nullable=True)


class HotelService(Base):
    __tablename__ = "services"
    __table_args__ = (CheckConstraint("price > 0", name="ck_service_price"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    unit: Mapped[str] = mapped_column(String(30), default="lần")
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class ServiceUsage(Base):
    __tablename__ = "service_usages"
    __table_args__ = (CheckConstraint("quantity > 0", name="ck_usage_quantity"), CheckConstraint("unit_price >= 0", name="ck_usage_price"))
    id: Mapped[int] = mapped_column(primary_key=True)
    booking_id: Mapped[int] = mapped_column(ForeignKey("bookings.id"))
    service_id: Mapped[int] = mapped_column(ForeignKey("services.id"))
    quantity: Mapped[int] = mapped_column(default=1)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    used_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    booking: Mapped[Booking] = relationship(back_populates="service_usages")
    service: Mapped[HotelService] = relationship()


class Invoice(Base):
    __tablename__ = "invoices"
    __table_args__ = (
        CheckConstraint('room_amount >= 0 AND service_amount >= 0', name='ck_invoice_amounts'),
        CheckConstraint('discount >= 0 AND discount <= room_amount + service_amount + surcharge_amount', name='ck_invoice_discount'),
        CheckConstraint('total = room_amount + service_amount + surcharge_amount - discount', name='ck_invoice_total'),
        CheckConstraint('surcharge_amount >= 0',name='ck_invoice_surcharge'),
        CheckConstraint('paid_amount >= 0 AND paid_amount <= total', name='ck_invoice_paid'),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    booking_id: Mapped[int] = mapped_column(ForeignKey("bookings.id"), unique=True)
    room_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    service_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    surcharge_amount: Mapped[Decimal] = mapped_column(Numeric(12,2),server_default='0')
    discount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    paid_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    payment_status: Mapped[PaymentStatus] = mapped_column(SQLEnum(PaymentStatus), default=PaymentStatus.unpaid)
    issued_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    booking: Mapped[Booking] = relationship(back_populates="invoice")
    payments: Mapped[list["Payment"]] = relationship(back_populates="invoice", order_by="Payment.paid_at")


class BookingStatusHistory(Base):
    __tablename__ = "booking_status_history"
    id: Mapped[int] = mapped_column(primary_key=True)
    booking_id: Mapped[int] = mapped_column(ForeignKey("bookings.id"), index=True)
    from_status: Mapped[BookingStatus] = mapped_column(SQLEnum(BookingStatus), nullable=True)
    to_status: Mapped[BookingStatus] = mapped_column(SQLEnum(BookingStatus))
    changed_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=True)
    changed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    booking: Mapped[Booking] = relationship(back_populates="status_history")


class Payment(Base):
    __tablename__ = "payments"
    __table_args__ = (CheckConstraint("amount > 0", name="ck_payments_positive_amount"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("invoices.id"), index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    paid_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=True)
    paid_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    invoice: Mapped[Invoice] = relationship(back_populates="payments")


class MoneyEntry(Base):
    __tablename__='money_entries'
    __table_args__=(UniqueConstraint('booking_id','request_key',name='uq_money_request'),CheckConstraint('amount > 0',name='ck_money_positive'),CheckConstraint("kind IN ('deposit','payment','refund','legacy_opening')",name='ck_money_kind'),CheckConstraint("method IN ('cash','bank_transfer','unknown')",name='ck_money_method'))
    id: Mapped[int]=mapped_column(primary_key=True)
    booking_id: Mapped[int]=mapped_column(ForeignKey('bookings.id'),index=True)
    payment_id: Mapped[int]=mapped_column(ForeignKey('payments.id'),unique=True,nullable=True)
    amount: Mapped[Decimal]=mapped_column(Numeric(12,2))
    kind: Mapped[str]=mapped_column(String(20))
    method: Mapped[str]=mapped_column(String(20))
    reference: Mapped[str]=mapped_column(String(100),default='')
    reason: Mapped[str]=mapped_column(String(500),server_default='')
    request_key: Mapped[str]=mapped_column(String(64))
    actor_id: Mapped[int]=mapped_column(ForeignKey('users.id'),nullable=True)
    shift_id: Mapped[int]=mapped_column(ForeignKey('cashier_shifts.id'),nullable=True,index=True)
    occurred_at: Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)


class CashierShift(Base):
    __tablename__='cashier_shifts'
    __table_args__=(CheckConstraint("status IN ('open','closed')",name='ck_shift_status'),CheckConstraint('opening_cash >= 0 AND (counted_cash IS NULL OR counted_cash >= 0)',name='ck_shift_amounts'),Index('uq_shift_open_cashier','cashier_id',unique=True,sqlite_where=text("status='open'"),postgresql_where=text("status='open'")))
    id: Mapped[int]=mapped_column(primary_key=True)
    cashier_id: Mapped[int]=mapped_column(ForeignKey('users.id'))
    status: Mapped[str]=mapped_column(String(10),default='open')
    opened_at: Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)
    closed_at: Mapped[datetime]=mapped_column(DateTime,nullable=True)
    opening_cash: Mapped[Decimal]=mapped_column(Numeric(12,2))
    counted_cash: Mapped[Decimal]=mapped_column(Numeric(12,2),nullable=True)
    expected_cash: Mapped[Decimal]=mapped_column(Numeric(14,2),nullable=True)
    difference: Mapped[Decimal]=mapped_column(Numeric(14,2),nullable=True)
    handed_to: Mapped[int]=mapped_column(ForeignKey('users.id'),nullable=True)
    note: Mapped[str]=mapped_column(String(2000),default='')
    snapshot_json: Mapped[str]=mapped_column(Text,default='{}')


class AIResult(Base):
    __tablename__ = "ai_results"
    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(30), index=True)
    content: Mapped[str] = mapped_column(Text)
    email_kind: Mapped[str] = mapped_column(String(30),server_default='')
    model_name: Mapped[str] = mapped_column(String(80),server_default='legacy/unknown')
    prompt_version: Mapped[str] = mapped_column(String(40),server_default='legacy/unknown')
    source_json: Mapped[str] = mapped_column(Text,server_default='{}')
    booking_id: Mapped[int] = mapped_column(ForeignKey("bookings.id"), nullable=True)
    review_status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    generated_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    reviewed_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    reviewed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)


class DemoSeed(Base):
    __tablename__='demo_seeds'
    name: Mapped[str]=mapped_column(String(60),primary_key=True)
    anchor_date: Mapped[date]=mapped_column(Date)
    created_at: Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)


class AIReviewEvent(Base):
    __tablename__='ai_review_events'
    id: Mapped[int]=mapped_column(primary_key=True)
    result_id: Mapped[int]=mapped_column(ForeignKey('ai_results.id'),index=True)
    actor_id: Mapped[int]=mapped_column(ForeignKey('users.id'))
    approved: Mapped[bool]=mapped_column(Boolean)
    created_at: Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)


class HotelPolicy(Base):
    __tablename__='hotel_policy'
    __table_args__=(CheckConstraint('id=1',name='ck_policy_singleton'),CheckConstraint('check_in_hour BETWEEN 0 AND 23 AND check_out_hour BETWEEN 0 AND 23 AND no_show_hour BETWEEN 0 AND 23',name='ck_policy_hours'),CheckConstraint('early_fee >= 0 AND late_fee >= 0',name='ck_policy_fees'),CheckConstraint('cancellation_percent BETWEEN 0 AND 100 AND no_show_percent BETWEEN 0 AND 100',name='ck_policy_cancellation'))
    id: Mapped[int]=mapped_column(primary_key=True)
    check_in_hour: Mapped[int]=mapped_column(default=14)
    check_out_hour: Mapped[int]=mapped_column(default=12)
    no_show_hour: Mapped[int]=mapped_column(default=23)
    early_fee: Mapped[Decimal]=mapped_column(Numeric(12,2),default=0)
    late_fee: Mapped[Decimal]=mapped_column(Numeric(12,2),default=0)
    cancellation_percent: Mapped[Decimal]=mapped_column(Numeric(5,2),server_default='0')
    no_show_percent: Mapped[Decimal]=mapped_column(Numeric(5,2),server_default='0')


class FinancialAdjustment(Base):
    __tablename__='financial_adjustments'
    __table_args__=(CheckConstraint("target_status IN ('cancelled','no_show')",name='ck_adjustment_status'),CheckConstraint('percent >= 0 AND percent <= 100 AND fee_amount >= 0 AND fee_amount <= original_total AND amount = fee_amount - original_total',name='ck_adjustment_math'))
    id: Mapped[int]=mapped_column(primary_key=True)
    booking_id: Mapped[int]=mapped_column(ForeignKey('bookings.id'),unique=True)
    target_status: Mapped[str]=mapped_column(String(20))
    original_total: Mapped[Decimal]=mapped_column(Numeric(12,2))
    fee_amount: Mapped[Decimal]=mapped_column(Numeric(12,2))
    percent: Mapped[Decimal]=mapped_column(Numeric(5,2))
    amount: Mapped[Decimal]=mapped_column(Numeric(12,2))
    reason: Mapped[str]=mapped_column(String(500))
    request_key: Mapped[str]=mapped_column(String(64))
    actor_id: Mapped[int]=mapped_column(ForeignKey('users.id'))
    created_at: Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)


class BookingSurcharge(Base):
    __tablename__='booking_surcharges'
    __table_args__=(UniqueConstraint('booking_id','kind',name='uq_booking_surcharge'),CheckConstraint("kind IN ('early','late')",name='ck_surcharge_kind'),CheckConstraint('amount > 0',name='ck_surcharge_amount'))
    id: Mapped[int]=mapped_column(primary_key=True)
    booking_id: Mapped[int]=mapped_column(ForeignKey('bookings.id'),index=True)
    kind: Mapped[str]=mapped_column(String(10))
    amount: Mapped[Decimal]=mapped_column(Numeric(12,2))
    confirmed_by: Mapped[int]=mapped_column(ForeignKey('users.id'))
    confirmed_at: Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)
