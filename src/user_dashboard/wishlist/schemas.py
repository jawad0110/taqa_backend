from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import uuid

from src.db.models import Wishlist
from src.user_dashboard.products.schemas import ProductImageRead


class WishlistCreateModel(BaseModel):
    product_uid: str


class WishlistModel(BaseModel):
    uid: str
    user_uid: str
    product_uid: str
    added_at: datetime
    updated_at: datetime
    product: Optional[dict] = None

    class Config:
        from_attributes = True


class ProductSummaryModel(BaseModel):
    uid: str
    title: str
    price: float
    main_image: Optional[str] = None
    in_stock: bool
    stock_status: Optional[str] = None
    images: Optional[list[ProductImageRead]] = []

    class Config:
        from_attributes = True


class WishlistResponseModel(BaseModel):
    uid: str
    product_uid: str
    added_at: datetime
    product: ProductSummaryModel

    class Config:
        from_attributes = True
