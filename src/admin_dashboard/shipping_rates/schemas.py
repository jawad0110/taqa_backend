from pydantic import BaseModel
from typing import Optional
import uuid

class ShippingRateBase(BaseModel):
    country: str
    city: str
    price: float

class ShippingRateCreate(ShippingRateBase):
    pass

class ShippingRateUpdate(BaseModel):
    country: Optional[str] = None
    city: Optional[str] = None
    price: Optional[float] = None

class ShippingRateResponse(ShippingRateBase):
    uid: uuid.UUID
