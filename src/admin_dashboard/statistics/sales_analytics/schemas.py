from pydantic import BaseModel
from typing import List
from datetime import datetime

class SalesPeriod(BaseModel):
    orders: int
    revenue: float

class MonthlySales(SalesPeriod):
    month: int

class DailySales(SalesPeriod):
    day: int

class WeeklySales(SalesPeriod):
    day_of_week: str

class TopSellingProduct(BaseModel):
    id: str
    name: str
    price: float
    stock: int
    is_active: bool
    sales: int

class SalesAnalytics(BaseModel):
    yearly_sales: List[MonthlySales]
    monthly_sales: List[DailySales]
    weekly_sales: List[WeeklySales]
    total_revenue: float
    conversion_rate: float
    top_selling_products: List[TopSellingProduct]
