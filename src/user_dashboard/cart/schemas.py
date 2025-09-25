from datetime import datetime
from typing import Optional
import uuid
from pydantic import BaseModel, Field

class CartModel(BaseModel):
    uid: uuid.UUID
    product_uid: uuid.UUID
    variant_choice_id: Optional[uuid.UUID] = None
    product_title: str
    main_image_url: Optional[str] = None
    quantity: int = Field(default=1, gt=0)
    price: float
    total_price: float  # Add this field
    user_uid: uuid.UUID
    added_at: datetime 
    updated_at: datetime
    stock: int  # Available stock for this item (product stock or variant stock)

    class Config:
        from_attributes = True  # no longer strictly needed


class CartCreateModel(BaseModel):
    product_uid: uuid.UUID
    variant_choice_id: Optional[uuid.UUID] = None
    quantity: int = Field(default=1, gt=0)
    
class CartUpdateModel(BaseModel):
    variant_choice_id: Optional[uuid.UUID] = None
    quantity: int = Field(default=1, gt=0)