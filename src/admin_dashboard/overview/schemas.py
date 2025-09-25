from pydantic import BaseModel
from typing import Optional

class OverviewStats(BaseModel):
    total_products: int
    total_orders: int
    total_users: int
    average_price: float
    low_stock_count: int
    total_storage_mb: float
    total_earnings: Optional[float] = None
    total_revenue: Optional[float] = None
    total_costs: Optional[float] = None
    total_delivery_fees: Optional[float] = None
    total_discounts: Optional[float] = None
