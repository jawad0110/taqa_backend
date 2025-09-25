from fastapi import UploadFile
from pydantic import BaseModel, Field, ConfigDict, field_serializer, model_serializer
from datetime import datetime
import uuid
from decimal import Decimal
from typing import List, Optional, TypeVar, Generic, Union, Dict, Any, Annotated
from src.admin_dashboard.reviews.schemas import ReviewModel

# Custom type for Decimal fields
DecimalField = Annotated[float, Field(json_schema={"type": "number", "format": "decimal"})]


T = TypeVar('T')

class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int
    limit: int
    total_pages: int



class Product(BaseModel):
    uid: uuid.UUID
    title: str
    description: str
    price: DecimalField
    cost_price: DecimalField  # Add this field
    stock: int = Field(ge=0)
    stock_status: Optional[str] = None
    main_image: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={
            Decimal: lambda v: float(round(v, 2))
        },
        arbitrary_types_allowed=True
    )
    
    @field_serializer('price', 'cost_price')  # Add cost_price here
    def serialize_prices(self, value: Decimal) -> float:
        return float(round(Decimal(str(value)), 2))
    
    
    
    
    
class VariantChoiceBase(BaseModel):
    value: str
    stock: int = Field(ge=0)  # Required stock field with minimum value of 0
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

class VariantChoiceCreate(VariantChoiceBase):
    pass

class VariantChoiceUpdate(BaseModel):
    value: Optional[str] = None
    stock: int = Field(ge=0)
    extra_price: Optional[DecimalField] = None

class VariantChoiceRead(VariantChoiceBase):
    id: uuid.UUID
    is_available: bool = True  # Default True, will be set in service logic
    model_config = ConfigDict(from_attributes=True)

class VariantGroupBase(BaseModel):
    name: str

class VariantGroupCreate(VariantGroupBase):
    choices: List[VariantChoiceCreate]

class VariantGroupUpdate(BaseModel):
    name: Optional[str] = None
    choices: Optional[List[VariantChoiceCreate]] = None  # For full replacement

class VariantGroupRead(VariantGroupBase):
    id: uuid.UUID
    choices: List[VariantChoiceRead]
    model_config = ConfigDict(from_attributes=True)

class ProductDetailModel(Product):
    images: List[str] = []
    variant_groups: List[VariantGroupRead] = []
    reviews: List[ReviewModel] = []


class ProductDetail_Category(Product):
    pass


class ProductCreateModel(BaseModel):
    title: str
    description: str
    price: DecimalField
    cost_price: DecimalField = Field(default=0.0)  # Add this field
    stock: int = Field(ge=0)
    is_active: bool
    
    model_config = ConfigDict(
        json_encoders={
            Decimal: lambda v: float(round(v, 2))
        },
        arbitrary_types_allowed=True
    )
    
    @field_serializer('price', 'cost_price')  # Add cost_price here
    def serialize_prices(self, value: Decimal) -> float:
        return float(round(Decimal(str(value)), 2))
    
    
    
    
    
class VariantChoiceBase(BaseModel):
    value: str
    stock: int = Field(ge=0)  # Required stock field with minimum value of 0
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

class VariantChoiceCreate(VariantChoiceBase):
    pass

class VariantChoiceUpdate(BaseModel):
    value: Optional[str] = None
    stock: int = Field(ge=0)
    extra_price: Optional[DecimalField] = None

class VariantChoiceRead(VariantChoiceBase):
    id: uuid.UUID
    is_available: bool = True  # Default True, will be set in service logic
    model_config = ConfigDict(from_attributes=True)

class VariantGroupBase(BaseModel):
    name: str

class VariantGroupCreate(VariantGroupBase):
    choices: List[VariantChoiceCreate]

class VariantGroupUpdate(BaseModel):
    name: Optional[str] = None
    choices: Optional[List[VariantChoiceCreate]] = None  # For full replacement

class VariantGroupRead(VariantGroupBase):
    id: uuid.UUID
    choices: List[VariantChoiceRead]
    model_config = ConfigDict(from_attributes=True)

class ProductDetailModel(Product):
    images: List[str] = []
    variant_groups: List[VariantGroupRead] = []
    reviews: List[ReviewModel] = []


class ProductDetail_Category(Product):
    pass


# Admin-specific output model (if needed)
class ProductAdmin(Product):
    pass
    
    
    
class ProductUpdateModel(BaseModel):
    title: str
    description: str
    price: DecimalField
    cost_price: DecimalField  # Add this field
    stock: int = Field(ge=0)
    is_active: bool
    
    model_config = ConfigDict(
        json_encoders={
            Decimal: lambda v: float(round(v, 2))
        },
        arbitrary_types_allowed=True
    )
    
    @field_serializer('price', 'cost_price')  # Add cost_price here
    def serialize_prices(self, value: Decimal) -> float:
        return float(round(Decimal(str(value)), 2))



class ProductImageBase(BaseModel):
    filename: str
    is_main: bool = False

class ProductImageCreate(ProductImageBase):
    pass

class ProductImageUpdate(BaseModel):
    is_main: Optional[bool] = None

class ProductImageRead(ProductImageBase):
    uid: uuid.UUID
    product_uid: uuid.UUID
    created_at: datetime
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

PaginatedProductResponse = PaginatedResponse[Union[Product, ProductAdmin]]
