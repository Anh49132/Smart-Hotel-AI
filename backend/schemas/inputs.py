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


class PasswordIn(BaseModel):
    password: str = Field(min_length=8, max_length=72)

    @field_validator('password')
    @classmethod
    def bcrypt_length(cls, value):
        if len(value.encode('utf-8')) > 72:
            raise ValueError('Mật khẩu tối đa 72 byte UTF-8')
        return value


class PasswordChange(PasswordIn):
    current_password: str = Field(min_length=1, max_length=72)


class UserRoleIn(BaseModel):
    role: Role


class UserCreate(PasswordIn):
    username: str = Field(min_length=3, max_length=50, pattern=r'^[A-Za-z0-9_.-]+$')
    full_name: str = Field(min_length=1, max_length=120)
    role: Role


class RoomTypeIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    capacity: int = Field(ge=1, le=20)
    nightly_rate: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    amenities: str = ""
    weekend_rate: Optional[Decimal] = Field(default=None, gt=0, max_digits=12, decimal_places=2)
    is_active: bool = True


class RatePlanIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    start_date: date
    end_date: date
    nightly_rate: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    is_active: bool = True

    @model_validator(mode='after')
    def dates(self):
        if self.end_date <= self.start_date:
            raise ValueError('Ngày kết thúc phải sau ngày bắt đầu (không gồm ngày kết thúc)')
        return self


class RoomIn(BaseModel):
    number: str
    floor: int = Field(ge=0)
    room_type_id: int
    status: RoomStatus = RoomStatus.available


class CustomerIn(BaseModel):
    full_name: str = Field(min_length=1,max_length=120)
    phone: str = Field(min_length=3,max_length=30)
    email: Optional[EmailStr] = None
    identity_number: Optional[str] = Field(default=None,max_length=80)
    preference_notes: str = Field(default='',max_length=2000)
    clear_identity: bool = False


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
        if (self.check_out - self.check_in).days > 365:
            raise ValueError('Mỗi đặt phòng tối đa 365 đêm')
        return self


class ServiceIn(BaseModel):
    name: str
    unit: str = "lần"
    price: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    active: bool = True


class BookingChangeIn(BaseModel):
    room_id: int
    check_in: date
    check_out: date
    reason: str = Field(min_length=3, max_length=500)
    expected_total: Optional[Decimal] = Field(default=None, ge=0, max_digits=12, decimal_places=2)

    @model_validator(mode='after')
    def dates(self):
        if not 1 <= (self.check_out-self.check_in).days <= 365:
            raise ValueError('Khoảng lưu trú phải từ 1 đến 365 đêm')
        return self


class ServiceUsageIn(BaseModel):
    booking_id: int
    service_id: int
    quantity: int = Field(ge=1)


class PaymentIn(BaseModel):
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    method: Literal['cash','bank_transfer'] = 'cash'
    reference: str = Field(default='',max_length=100)
    request_key: Optional[str] = Field(default=None,min_length=8,max_length=64,pattern=r'^[A-Za-z0-9_-]+$')


class ReceiptIn(PaymentIn):
    request_key: str = Field(min_length=8,max_length=64,pattern=r'^[A-Za-z0-9_-]+$')
    kind: Literal['deposit','payment'] = 'deposit'


class RoomAdviceIn(BaseModel):
    guests: int = Field(ge=1)
    budget: Decimal = Field(gt=0)
    check_in: date
    check_out: date
    amenities: str = ""

    @model_validator(mode='after')
    def stay_dates(self):
        if not 1 <= (self.check_out - self.check_in).days <= 365:
            raise ValueError('Khoảng lưu trú phải từ 1 đến 365 đêm')
        return self


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
