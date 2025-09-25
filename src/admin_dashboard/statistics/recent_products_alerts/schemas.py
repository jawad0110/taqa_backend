from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
import uuid

class RecentProduct(BaseModel):
    id: uuid.UUID
    title: str
    created_at: datetime

class AlertItem(BaseModel):
    id: uuid.UUID
    title: str

class OutOfStockProduct(BaseModel):
    id: str = Field(..., alias='id')
    title: str
    stock: int
    has_variants: bool = False

class Alerts(BaseModel):
    missing_main_image: List[AlertItem]
    out_of_stock: List[OutOfStockProduct]
    
    class Config:
        json_encoders = {
            uuid.UUID: lambda v: str(v)
        }
