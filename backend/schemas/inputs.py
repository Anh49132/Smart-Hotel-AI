from backend.models import BookingStatus, PaymentStatus, Role, RoomStatus
from datetime import date
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator
from typing import Literal, Optional

class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class LoginRequest(BaseModel):
    username: str
    password: str


class UserCreate(BaseModel):
    username: str
    full_name: str
    password: str = Field(min_length=8)
    role: Role


class RoomTypeIn(BaseModel):
    name: str
    capacity: int = Field(ge=1, le=20)
    nightly_rate: Decimal = Field(gt=0)
    amenities: str = ""


class RoomIn(BaseModel):
    number: str
    floor: int = Field(ge=0)
    room_type_id: int
    status: RoomStatus = RoomStatus.available


class CustomerIn(BaseModel):
    full_name: str
    phone: str
    email: Optional[EmailStr] = None
    identity_number: Optional[str] = None


class BookingIn(BaseModel):
    customer_id: int
    room_id: int
    check_in: date
    check_out: date
    guests: int = Field(ge=1)
    note: str = ""

    @model_validator(mode="after")
    def validate_dates(self):
        if self.check_out <= self.check_in:
            raise ValueError("Ngày trả phải sau ngày nhận")
        return self


class ServiceIn(BaseModel):
    name: str
    unit: str = "lần"
    price: Decimal = Field(gt=0)
    active: bool = True


class ServiceUsageIn(BaseModel):
    booking_id: int
    service_id: int
    quantity: int = Field(ge=1)


class PaymentIn(BaseModel):
    amount: Decimal = Field(gt=0)


class RoomAdviceIn(BaseModel):
    guests: int = Field(ge=1)
    budget: Decimal = Field(gt=0)
    check_in: date
    check_out: date
    amenities: str = ""


class EmailRequest(BaseModel):
    booking_id: int
    kind: str = Field(pattern="^(confirmation|cancellation|payment_reminder)$")


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=1500)

    @field_validator("content")
    @classmethod
    def clean_content(cls, value: str):
        value = value.strip()
        if not value:
            raise ValueError("Tin nhắn không được để trống")
        return value


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(min_length=1, max_length=12)

    @model_validator(mode="after")
    def require_latest_user_message(self):
        if self.messages[-1].role != "user":
            raise ValueError("Tin nhắn cuối cùng phải do người dùng gửi")
        return self
