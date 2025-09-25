from pydantic import BaseModel, Field, ConfigDict, EmailStr
from datetime import datetime
import uuid
from typing import List, Optional, TypeVar, Generic
from src.db.models import User, Profile

# Custom type for pagination
T = TypeVar('T')

class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int
    limit: int
    total_pages: int


class UserBase(BaseModel):
    username: str
    email: EmailStr
    first_name: str
    last_name: str
    role: str = Field(default="user")
    is_verified: bool = Field(default=False)


class UserCreate(UserBase):
    password: str = Field(min_length=8)


class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    role: Optional[str] = None
    is_verified: Optional[bool] = None


class UserVerificationUpdate(BaseModel):
    is_verified: bool


class UserResponse(UserBase):
    uid: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserDetailResponse(UserResponse):
    profile: Optional[dict] = None
    total_orders: int = 0
    total_reviews: int = 0
    total_cart_items: int = 0
    total_wishlist_items: int = 0


class UserListResponse(BaseModel):
    users: List[UserResponse]
    total: int
    page: int
    limit: int
    total_pages: int


class UserStatsResponse(BaseModel):
    total_users: int
    verified_users: int
    unverified_users: int
    admin_users: int
    regular_users: int
    recent_registrations: int  # Last 30 days
