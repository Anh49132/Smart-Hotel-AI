from core.database import Base
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, Enum as SQLEnum, ForeignKey, Index, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

class Role(str, Enum):
    admin = "admin"
    receptionist = "receptionist"
    accountant = "accountant"


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


class RoomType(Base):
    __tablename__ = "room_types"
    __table_args__ = (CheckConstraint("capacity > 0", name="ck_room_type_capacity"), CheckConstraint("nightly_rate > 0", name="ck_room_type_rate"))
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True)
    capacity: Mapped[int]
    nightly_rate: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    amenities: Mapped[str] = mapped_column(Text, default="")
    rooms: Mapped[list["Room"]] = relationship(back_populates="room_type")


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
    bookings: Mapped[list["Booking"]] = relationship(back_populates="customer")


class Booking(Base):
    __tablename__ = "bookings"
    __table_args__ = (CheckConstraint("check_out > check_in", name="ck_booking_dates"), CheckConstraint("guests > 0", name="ck_booking_guests"), Index('ix_booking_overlap', 'room_id', 'status', 'check_in', 'check_out'))
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(24), unique=True, index=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"))
    room_id: Mapped[int] = mapped_column(ForeignKey("rooms.id"), index=True)
    check_in: Mapped[date] = mapped_column(Date, index=True)
    check_out: Mapped[date] = mapped_column(Date, index=True)
    guests: Mapped[int]
    status: Mapped[BookingStatus] = mapped_column(SQLEnum(BookingStatus), default=BookingStatus.confirmed)
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    customer: Mapped[Customer] = relationship(back_populates="bookings")
    room: Mapped[Room] = relationship()
    service_usages: Mapped[list["ServiceUsage"]] = relationship(back_populates="booking", cascade="all, delete-orphan")
    invoice: Mapped["Invoice"] = relationship(back_populates="booking", uselist=False)
    status_history: Mapped[list["BookingStatusHistory"]] = relationship(back_populates="booking", order_by="BookingStatusHistory.changed_at")


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
    id: Mapped[int] = mapped_column(primary_key=True)
    booking_id: Mapped[int] = mapped_column(ForeignKey("bookings.id"), unique=True)
    room_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    service_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
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


class AIResult(Base):
    __tablename__ = "ai_results"
    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(30), index=True)
    content: Mapped[str] = mapped_column(Text)
    booking_id: Mapped[int] = mapped_column(ForeignKey("bookings.id"), nullable=True)
    review_status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    generated_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    reviewed_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    reviewed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
