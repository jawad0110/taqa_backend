from pydantic import BaseModel, Field, ConfigDict, field_serializer
from typing import List, Optional, Annotated
from datetime import datetime
import uuid
from decimal import Decimal

from src.db.models import OrderStatus
from src.user_dashboard.checkouts.schemas import ShippingAddressModel, OrderItemResponse

# Reuse a float alias for Decimal values in responses
DecimalField = Annotated[float, Field(json_schema={"type": "number", "format": "decimal"})]

from src.db.models import User

class OrderResponse(BaseModel):
    uid: str
    user_uid: uuid.UUID
    first_name: str
    last_name: str
    status: OrderStatus
    total_price: DecimalField
    shipping_price: DecimalField
    discount: DecimalField
    final_price: DecimalField
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

    @field_serializer('total_price', 'shipping_price', 'discount', 'final_price')
    def _serialize_prices(self, value: Decimal) -> float:
        return float(round(Decimal(str(value)), 2))

class UpdateOrderStatus(BaseModel):
    status: OrderStatus

class PaginatedOrderResponse(BaseModel):
    orders: List[OrderResponse]
    total: int
    page: int
    per_page: int
    total_pages: int