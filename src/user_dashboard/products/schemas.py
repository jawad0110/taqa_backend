from pydantic import BaseModel, Field, ConfigDict, field_serializer
from datetime import datetime
import uuid
from decimal import Decimal
from typing import List, Optional, TypeVar, Union, Dict, Any, Annotated

# Custom type for Decimal fields
DecimalField = Annotated[float, Field(json_schema={"type": "number", "format": "decimal"})]

class ProductImageRead(BaseModel):
    uid: uuid.UUID
    filename: str
    is_main: bool
    
    model_config = ConfigDict(from_attributes=True)

from src.admin_dashboard.reviews.schemas import ReviewModel
from src.admin_dashboard.products.schemas import Product, PaginatedResponse

T = TypeVar('T')

class Product(BaseModel):
    uid: uuid.UUID
    title: str
    description: str
    price: DecimalField
    main_image: Optional[str] = None
    stock_status: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    model_config = ConfigDict(
        json_encoders={
            Decimal: lambda v: float(round(v, 2))  # Convert Decimal to float with 2 decimal places
        },
        arbitrary_types_allowed=True
    )
    
    @field_serializer('price')
    def serialize_prices(self, value: Decimal) -> float:
        return float(round(Decimal(str(value)), 2))  # Ensure proper decimal rounding

class ProductRead(Product):
    category_uid: Optional[uuid.UUID] = None
    is_active: bool = True
    updated_at: datetime
    category: Optional[Dict[str, Any]] = None
    main_image: Optional[str] = None  # For list responses
    images: List[ProductImageRead] = []  # For detail responses
    # --- Stock fields ---
    stock: int
    stock_status: Optional[str] = None  # 'In Stock', 'Out of Stock', 'Unlimited'
    created_at: Optional[datetime] = None

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        arbitrary_types_allowed=True
    )


class ProductDetail_Category(Product):
    pass


class VariantChoiceModel(BaseModel):
    id: uuid.UUID
    value: str
    stock: Optional[int] = None
    extra_price: Optional[DecimalField] = None
    
    model_config = ConfigDict(
        json_encoders={
            Decimal: lambda v: float(round(v, 2))  # Convert Decimal to float with 2 decimal places
        },
        arbitrary_types_allowed=True
    )
    
    @field_serializer('extra_price')
    def serialize_extra_price(self, value: Optional[Decimal]) -> Optional[float]:
        return float(round(Decimal(str(value)), 2)) if value is not None else None

class VariantGroupModel(BaseModel):
    id: uuid.UUID
    name: str
    choices: List[VariantChoiceModel]

class ProductDetail(Product):
    main_image: Optional[str] = None
    images: List[ProductImageRead] = []
    variant_groups: List[VariantGroupModel] = []
    reviews: List[ReviewModel] = []
    
    # --- Stock fields ---
    stock: int
    stock_status: Optional[str] = None  # 'In Stock', 'Out of Stock', 'Unlimited'
    
    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        json_encoders={
            Decimal: lambda v: float(round(v, 2))  # Convert Decimal to float with 2 decimal places
        },
        arbitrary_types_allowed=True
    )


# Add paginated response types
PaginatedProductResponse = PaginatedResponse[Union[Product]]
