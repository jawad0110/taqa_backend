from datetime import datetime
from typing import List, Optional, Annotated
import uuid
from pydantic import BaseModel, Field, ConfigDict, field_serializer
from decimal import Decimal

from src.db.models import OrderStatus

class ShippingAddressInput(BaseModel):
    full_name: str
    phone_number: str
    country: str
    city: str
    area: str
    street: str
    building_number: Optional[str] = None
    apartment_number: Optional[str] = None
    zip_code: Optional[str] = None
    notes: Optional[str] = None

class CheckoutCreate(BaseModel):
    shipping_address: ShippingAddressInput
    coupon_code: Optional[str] = None

class ProductDetail(BaseModel):
    uid: uuid.UUID
    title: str
    main_image_url: Optional[str] = None
    variant_groups: List[dict] = []

class OrderItemResponse(BaseModel):
    uid: uuid.UUID
    product: ProductDetail
    quantity: int
    price_at_purchase: Annotated[float, Field(json_schema={"type": "number", "format": "decimal"})]
    total_price: Annotated[float, Field(json_schema={"type": "number", "format": "decimal"})]
    variant_choice_id: Optional[uuid.UUID] = None

class ShippingAddressModel(BaseModel):
    uid: uuid.UUID
    full_name: str
    phone_number: str
    country: str
    city: str
    area: str
    street: str
    building_number: Optional[str] = None
    apartment_number: Optional[str] = None
    zip_code: Optional[str] = None
    notes: Optional[str] = None

class CheckoutResponse(BaseModel):
    uid: str
    status: OrderStatus
    total_price: Annotated[float, Field(json_schema={"type": "number", "format": "decimal"})]
    discount: Annotated[float, Field(json_schema={"type": "number", "format": "decimal"})]
    shipping_price: Annotated[float, Field(json_schema={"type": "number", "format": "decimal"})]
    final_price: Annotated[float, Field(json_schema={"type": "number", "format": "decimal"})]
    coupon_code: Optional[str] = None
    created_at: datetime
    shipping_address: ShippingAddressModel
    items: List[OrderItemResponse]

    model_config = ConfigDict(
        json_encoders={
            Decimal: lambda v: float(round(v, 2))
        },
        arbitrary_types_allowed=True,
        from_attributes=True,
    )

    @field_serializer('total_price', 'discount', 'shipping_price', 'final_price')
    def _serialize_prices(self, value: Decimal) -> float:
        return float(round(Decimal(str(value)), 2))