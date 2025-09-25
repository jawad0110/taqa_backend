from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import uuid

class DiscountBase(BaseModel):
    code: str
    discount_type: str  # "percent" or "amount"
    value: float
    minimum_order_amount: Optional[float] = None
    expires_at: Optional[datetime] = None
    usage_limit: Optional[int] = None
    is_active: bool = True

class DiscountCreate(DiscountBase):
    pass

class DiscountUpdate(BaseModel):
    discount_type: Optional[str]
    value: Optional[float]
    minimum_order_amount: Optional[float] = None
    expires_at: Optional[datetime] = None
    usage_limit: Optional[int] = None
    is_active: Optional[bool]

class DiscountResponse(DiscountBase):
    uid: uuid.UUID
    used_count: int
    created_at: datetime
